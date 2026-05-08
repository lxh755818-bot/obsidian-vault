---
name: observer-hook-injection
description: Re-apply Observer/Instinct hooks after upstream Hermes Agent pull. Handles model_tools.py, agent/skill_commands.py, run_agent.py, hermes_cli/plugins.py. Run after git pull.
category: mlops
---

# Observer Hook Injection

Re-apply the `pre_tool_verification` and `post_tool_self_review` hooks after pulling upstream Hermes Agent updates.

## When to Run

After `git pull` if conflicts occur in any of these files:
- `model_tools.py`
- `agent/skill_commands.py`
- `run_agent.py`
- `hermes_cli/plugins.py`

## Hooks Being Injected

### 1. hermes_cli/plugins.py — VALID_HOOKS
Add two new hooks to `VALID_HOOKS`:
```python
    "post_tool_self_review",
    "pre_tool_verification",
```

### 2. model_tools.py — handle_function_call dispatch block

Replace the simple dispatch block:
```python
        _dispatch_start = time.monotonic()
        if function_name == "execute_code":
            sandbox_enabled = enabled_tools if enabled_tools is not None else _last_resolved_tool_names
            result = registry.dispatch(
                function_name, function_args,
                task_id=task_id,
                enabled_tools=sandbox_enabled,
            )
        else:
            result = registry.dispatch(
                function_name, function_args,
                task_id=task_id,
                user_task=user_task,
            )
        duration_ms = int((time.monotonic() - _dispatch_start) * 1000)

        try:
            from hermes_cli.plugins import invoke_hook
            invoke_hook(
                "post_tool_call",
                tool_name=function_name,
                args=function_args,
                result=result,
                task_id=task_id or "",
                session_id=session_id or "",
                tool_call_id=tool_call_id or "",
                duration_ms=duration_ms,
            )
        except Exception:
            pass
```

With the full pre-tool verification + dispatch + post-self-review block:
```python
        # ── Pre-tool verification gate ────────────────────────────────────────
        try:
            from hermes_cli.plugins import invoke_hook as _invoke_verification
            vresult = _invoke_verification(
                "pre_tool_verification",
                tool_name=function_name,
                args=function_args,
                context={
                    "session_id": session_id or "",
                    "task_id": task_id or "",
                    "directory": getattr(registry, "_cwd", ""),
                },
            )
            if vresult:
                _blocked = vresult.get("blocked", False)
                if _blocked:
                    reason = vresult.get("reason", "Verification blocked")
                    suggestion = vresult.get("suggestion", "")
                    logger.warning(
                        "VERIFICATION BLOCKED tool=%s reason=%s suggestion=%s",
                        function_name,
                        reason,
                        suggestion,
                    )
                    raise PermissionError(
                        f"Verification blocked: {reason}\\nSuggestion: {suggestion}"
                    )
                if vresult.get("warning_only"):
                    logger.info(
                        "VERIFICATION WARNING tool=%s instinct=%s verification_id=%s",
                        function_name,
                        vresult.get("instinct_name", "unknown"),
                        vresult.get("verification_id", "n/a"),
                    )
        except PermissionError:
            raise
        except Exception:
            pass

        start_time = time.monotonic()
        try:
            if function_name == "execute_code":
                sandbox_enabled = enabled_tools if enabled_tools is not None else _last_resolved_tool_names
                result = registry.dispatch(
                    function_name, function_args,
                    task_id=task_id,
                    enabled_tools=sandbox_enabled,
                )
            else:
                result = registry.dispatch(
                    function_name, function_args,
                    task_id=task_id,
                    user_task=user_task,
                )
            duration_ms = (time.monotonic() - start_time) * 1000
        except Exception as dispatch_error:
            duration_ms = (time.monotonic() - start_time) * 1000
            raise

        tool_call_error: Optional[str] = None
        tool_result_for_review = result

        # ── Inline self-review ────────────────────────────────────────────
        try:
            from hermes_cli.plugins import invoke_hook as _invoke_review
            review_results = _invoke_review(
                "post_tool_self_review",
                tool_name=function_name,
                args=function_args,
                result=tool_result_for_review,
                duration_ms=duration_ms,
                task_id=task_id or "",
                session_id=session_id or "",
            )
            if review_results:
                warnings = [r for r in review_results if r]
                if warnings:
                    logger.debug(
                        "Self-review warnings for %s: %s",
                        function_name,
                        warnings,
                    )
        except Exception:
            pass

        try:
            from hermes_cli.plugins import invoke_hook
            invoke_hook(
                "post_tool_call",
                tool_name=function_name,
                args=function_args,
                result=result,
                task_id=task_id or "",
                session_id=session_id or "",
                tool_call_id=tool_call_id or "",
                duration_ms=duration_ms,
            )
        except Exception:
            pass
```

Also update the error handler to fire `post_tool_call` with error info:
```python
    except Exception as e:
        error_msg = f"Error executing {function_name}: {str(e)}"
        logger.exception(error_msg)
        try:
            from hermes_cli.plugins import invoke_hook
            invoke_hook(
                "post_tool_call",
                tool_name=function_name,
                args=function_args,
                result=None,
                task_id=task_id or "",
                session_id=session_id or "",
                tool_call_id=tool_call_id or "",
                error=str(e),
                duration_ms=duration_ms if "duration_ms" in dir() else 0.0,
            )
        except Exception:
            pass
        return json.dumps({"error": error_msg}, ensure_ascii=False)
```

### 3. agent/skill_commands.py — after_skill_loaded hook

In `build_skill_invocation_message`, after `activation_note` assignment, add:
```python
    # Inject skill chain awareness — tell the agent what's next in the workflow
    try:
        from hermes_agent.skill_chain import after_skill_loaded
        chain_note = after_skill_loaded(skill_name)
        if runtime_note:
            runtime_note = runtime_note + chain_note
        else:
            runtime_note = chain_note
    except Exception:
        pass  # Non-critical — chain hooks are best-effort
```

### 4. run_agent.py — build_pre_task_prompt injection

After `if skills_prompt: prompt_parts.append(skills_prompt)`, add:
```python
    # Inject skill chain state awareness — makes the workflow visible to the model
    try:
        from hermes_agent.skill_chain import build_pre_task_prompt
        chain_prompt = build_pre_task_prompt()
        if chain_prompt:
            prompt_parts.append(chain_prompt)
    except Exception:
        pass  # Non-critical
```

## Upgrade-Safe File Classification

After a `git pull`, files fall into three categories:

| 文件类型 | 示例 | 升级行为 | 处理方式 |
|---------|------|---------|---------|
| **追踪文件（升级重置）** | `model_tools.py`, `agent/skill_commands.py`, `run_agent.py`, `hermes_cli/main.py` | 上游更新会覆盖 | 重新注入 hook 或用 wrapper |
| **新文件（升级安全）** | `observer_cli.py`, `kb_cli.py`, `memory_cli.py`, `evolution/`, `observer/` | 上游没有，不会被覆盖 | 保持不变即可 |
| **配置文件** | `~/.hermes/hermes.yaml` | 通常不随上游更新 | 保持不变 |

### main.py 命令的 upgrade-safe 方案

`main.py` 是追踪文件（升级会重置），但其 CLI 命令改动可以完全不碰 `main.py`：

```bash
# 创建 wrapper 脚本在 ~/.hermes/bin/
mkdir -p ~/.hermes/bin

# hermes-instinct
cat > ~/.hermes/bin/hermes-instinct << 'EOF'
#!/bin/bash
exec python3 -m hermes_cli.observer_cli "$@" instinct
EOF
chmod +x ~/.hermes/bin/hermes-instinct

# hermes-verify
cat > ~/.hermes/bin/hermes-verify << 'EOF'
#!/bin/bash
exec python3 -m hermes_cli.observer_cli "$@" verify
EOF
chmod +x ~/.hermes/bin/hermes-verify

# hermes-observer
cat > ~/.hermes/bin/hermes-observer << 'EOF'
#!/bin/bash
exec python3 -m hermes_cli.observer_cli "$@" observer
EOF
chmod +x ~/.hermes/bin/hermes-observer

# hermes-memstore
cat > ~/.hermes/bin/hermes-memstore << 'EOF'
#!/bin/bash
exec python3 -m hermes_cli.memory_cli "$@"
EOF
chmod +x ~/.hermes/bin/hermes-memstore

# hermes-kb
cat > ~/.hermes/bin/hermes-kb << 'EOF'
#!/bin/bash
exec python3 -m hermes_cli.kb_cli "$@"
EOF
chmod +x ~/.hermes/bin/hermes-kb
```

调用时直接用路径：`~/.hermes/bin/hermes-instinct list`，无需改 `main.py`。

### 验证：检查哪些文件是追踪的

```bash
git status --short | grep "^[ M]" | awk '{print $2}'
```

如果返回中有 `hermes_cli/main.py` → 需要用 wrapper 方案。

## Known Dangling Hooks — Architecture Pitfalls

**Discovered 2026-04-29:** Several `on_session_end` / `on_session_finalize` hooks are registered by plugins but never invoked by any known call site. This is a Hermes architecture gap, not a plugin bug.

### Dangling: mem9 `on_session_end(messages)`

**Location:** `~/.hermes/plugins/mem9/__init__.py` line 830
**Registered via:** `ctx.register_memory_provider()` — NOT a hook registration
**Problem:** `PluginContext.register_memory_provider()` does NOT register lifecycle hooks. The `on_session_end` method exists and accepts full `messages` list, but `mem9` has no way to receive it.
**What it would do:** Smart ingest the conversation tail to mem9 server via `POST /v1alpha2/mem9s/memories` with `mode: "smart"`.
**Workaround:** Use a Cron that reads `state.db` sessions table instead.

### Dangling: LCM engine `on_session_end(session_id, messages)`

**Location:** `~/.hermes/plugins/hermes-lcm/engine.py` line 561
**Problem:** This is a method on the `LLM` class, but no call site in the codebase invokes it.
**What it would do:** Trigger LCM session finalization/compression.
**Current trigger:** LCM uses its own internal criteria (token budget, compaction threshold) to decide when to compress — not this method.

### Dangling: Observer `on_session_finalize`

**Location:** `~/.hermes/plugins/observer/__init__.py` line 59
**Registered:** Yes (`ctx.register_hook("on_session_finalize", on_session_finalize)`)
**Problem:** No known call site invokes `on_session_finalize`. The ObserverAgent starts on `on_session_start` but there is no corresponding finalize trigger from the gateway or agent loop.
**What it would do:** Flush the ObserverAgent's event buffer and stop.
**Current behavior:** ObserverAgent likely never gets stopped cleanly — events are only flushed on batch timeout.

### sessions table — available telemetry

**Location:** `~/.hermes/state.db > sessions`
**Always populated, regardless of dangling hooks:**

| Column | Type | Description |
|--------|------|-------------|
| `message_count` | int | Messages in session |
| `tool_call_count` | int | Tool invocations |
| `input_tokens` | int | Total input tokens |
| `output_tokens` | int | Total output tokens |
| `reasoning_tokens` | int | Reasoning token count |
| `api_call_count` | int | LLM API calls made |
| `estimated_cost_usd` | float | Cost estimate |
| `started_at` | float | Unix timestamp |
| `ended_at` | float | Unix timestamp |
| `end_reason` | str | `compression` / `cron_complete` / `None` |

This table is the correct data source for ASVP Service Telemetry — no hook required.

### Feishu adapter keyword detection — no-op

**Location:** `hermes-feishu-streaming-card` legacy adapters
**What exists:** Keyword signals for user reactions ("好了", "可以", "谢谢", etc.)
**Problem:** `LLM交互质量评估_evaluate()` is a no-op placeholder — the keywords are detected but never used for scoring.
**File:** `hook_runtime.py` has full `message.completed` event emission with `answer` and `duration` fields, but quality evaluation is not wired.

## Verification

After injection, run:
```bash
python3 -c "
from hermes_cli.plugins import VALID_HOOKS
assert 'pre_tool_verification' in VALID_HOOKS
assert 'post_tool_self_review' in VALID_HOOKS
import model_tools; print('model_tools.py OK')
from agent.skill_commands import build_skill_invocation_message; print('skill_commands.py OK')
import run_agent; print('run_agent.py OK')
"
```
