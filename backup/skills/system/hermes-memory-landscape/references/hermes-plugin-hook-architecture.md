# Hermes Plugin Hook 架构 — session-end hook 悬空问题

**发现时间：2026-04-29**

## 已知 session-end 相关 hooks

| Hook 名称 | 注册方 | 实现文件 | 调用方 | 状态 |
|-----------|--------|---------|--------|------|
| `on_session_end` | mem9 | `plugins/mem9/__init__.py:830` | ❌ 从未被调用 | 悬空 |
| `on_session_end` | LCM engine | `plugins/hermes-lcm/engine.py:561` | ❌ 从未被调用 | 悬空 |
| `on_session_finalize` | Observer | `plugins/observer/__init__.py:59` | Hermes 核心在 session 结束时调用 | ✅ 工作 |
| `on_session_start` | Observer | `plugins/observer/__init__.py:29` | Hermes 核心在 session 开始时调用 | ✅ 工作 |
| `pre/post_tool_call` | Observer, self_review, verification | 各 `__init__.py` | Hermes 核心在每次工具/LLM调用时调用 | ✅ 工作 |
| `post_tool_self_review` | self_review | `plugins/self_review/__init__.py:198` | Hermes 核心在 tool 结束后调用 | ✅ 工作 |

## 核心问题：mem9 的 on_session_end 从未被触发

mem9 插件在 `register()` 中**只注册了 memory provider**：

```python
# plugins/mem9/__init__.py:1080
def register(ctx) -> None:
    ctx.register_memory_provider(Mem9MemoryProvider())
    # ← 没有注册任何 hook！
```

它有完整的 `on_session_end(messages)` 方法（可处理完整对话历史做 smart ingest），
但该方法从未作为 hook 注册到 Hermes 核心。

对比 Observer 插件的正确姿势：

```python
# plugins/observer/__init__.py:255-260
def register(ctx) -> None:
    ctx.register_hook("on_session_start", on_session_start)
    ctx.register_hook("on_session_finalize", on_session_finalize)
    ctx.register_hook("pre_tool_call", pre_tool_call)
    ctx.register_hook("post_tool_call", post_tool_call)
    # ...
```

## 为什么 sessions 表可以绕过这个问题

`sessions` 表的 `ended_at` / `input_tokens` / `output_tokens` / `tool_call_count`
等字段在 session 结束时**由 Hermes 核心直接写入**，不依赖任何 plugin hook。

因此 ASVP 聚合和 daily-distill 等功能可以：
1. 直接查询 `state.db > sessions` 表
2. 完全绕过悬空的 session-end hooks
3. 实现增量聚合（记录 last_window_end）

## 工作区插件状态

```
~/.hermes/plugins/
├── observer/              ✅ 6个 hook 全部注册并工作
│   ├── on_session_start
│   ├── on_session_finalize
│   ├── pre/post_tool_call
│   └── pre/post_llm_call
├── self_review/            ✅ post_tool_self_review 工作
├── verification/          ✅ pre_tool_verification 工作
├── mem9/                  ⚠️ memory provider 工作，hook 悬空
├── hermes-lcm/            ⚠️ engine 有 on_session_end 但从未被调用
└── hermes-feishu-.../     ⚠️ hook_runtime 有事件系统，不注册 Hermes hook
```

## 验证 hook 是否被调用

```bash
# 检查 Hermes 核心是否在 session 结束时调用 on_session_end
grep -rn "on_session_end\|call_hook.*end\|session.*end" \
  ~/.hermes/ --include="*.py" 2>/dev/null | \
  grep -v __pycache__ | grep -v "def on_session_end"

# 预期结果：应该只在 plugin 的 register() 调用处出现
# 如果 Hermes 核心有调用，会在 run_agent.py / gateway.py / 等核心文件中出现
```

## 解决方案（未来）

要让 mem9 on_session_end 工作，需要在 Hermes 核心中调用它：

**方案 A：在 Hermes 核心添加 session-end hook 调用**
```python
# 在 run_agent.py 或 gateway.py 的 session 结束处添加：
ctx.call_hook("on_session_end", session_id=session_id, messages=messages)
```

**方案 B：用 Observer on_session_finalize 中转**
Observer 的 `on_session_finalize` 是工作的，可以在那里手动触发 mem9 的 session-end 逻辑。

**方案 C（当前采用）：绕过 hook，直接查 sessions 表**
ASVP Telemetry / daily-distill 等功能直接读 `state.db > sessions` 表，不依赖任何 hook。

## 命名混淆

- `on_session_end`：mem9 和 LCM engine 使用，**从未被 Hermes 核心调用**
- `on_session_finalize`：Observer 使用，**是 Hermes 核心实际调用的名称**

如果未来要让 session-end hook 工作，需要确认 Hermes 核心使用的是哪个名称。
