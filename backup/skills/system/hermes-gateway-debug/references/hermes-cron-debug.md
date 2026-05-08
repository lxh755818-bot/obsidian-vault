# Source: `hermes-cron-debug`

---
name: hermes-cron-debug
description: Debug why a Hermes cron job isn't picking up skill changes, with pattern matching on prompt_preview and output directory inspection.
version: 1.0.0
author: 小哈
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [cron, hermes, debugging, self-evolution]
---

# Hermes Cron Debug Skill

## Core Problem

When you update a skill's SKILL.md, existing cron jobs that reference that skill **do NOT automatically pick up the changes**. The cron job's prompt is frozen at creation time. This causes silent failures where new code in SKILL.md is never executed.

## Debugging Steps

### Step 1: Identify Cron Job ID

```bash
cronjob action=list
```

Find the `job_id` for the job using the skill.

### Step 2: Check prompt_preview for New Code

```bash
# Compare job's prompt_preview with current SKILL.md content
# If job prompt doesn't contain code that IS in SKILL.md → frozen
cronjob action=list | grep -A5 "job_id"
```

### Step 3: Check Output Directory

Cron output goes to `~/.hermes/cron/output/<job_id>/` (by job_id, NOT by job name):

```bash
ls ~/.hermes/cron/output/<job_id>/
```

### Step 4: Fix — Remove and Recreate

```bash
# 1. Remove old job (uses job_id from step 1)
cronjob action=remove job_id=<job_id>

# 2. Recreate with same skill reference
cronjob action=create \
  name="技能循环优化（含情报+Gap+Tree）" \
  schedule="0 */2 * * *" \
  repeat=999 \
  skills='["skill-cycle-optimizer"]' \
  deliver=local \
  prompt="## 技能循环优化自进化任务（完整版）..."
```

### Step 5: Verify

After next run, check that new code executed:
```bash
ls ~/.hermes/cron/output/<new_job_id>/
cat ~/.hermes/evolution_logs/<module>/latest.json  # verify new data written
```

## Key Patterns Discovered

### Pattern 1: gap_analyzer.py Syntax Bug
**File**: `hermes_agent/evolution/gap_analyzer.py`
**Bug**: Line 261 — list comprehension uses `g in gaps` instead of `g for g in gaps`:
```python
# WRONG:
"low": len([g in gaps if g.severity == "low"]),
# CORRECT:
"low": len([g for g in gaps if g.severity == "low"]),
```
**Symptom**: `SyntaxError: expected 'else' after 'if' expression`
**Fix**: `patch()` the file immediately when found.

### Pattern 2: SkillTree.render_tree Signature
**File**: `hermes_agent/evolution/skill_tree.py`
**Method**: `render_tree(root_skill: Optional[str] = None) -> str`
**CLI registration**: Use `root_skill=getattr(args, 'category', None) or "skill-tree-optimizer"`
**Do NOT use**: `category_filter=` — that parameter doesn't exist.

### Pattern 3: execute_code State Isolation
Each `execute_code` call is a **fresh Python process** — no variable or import persists across calls. If you need to chain operations, put everything in ONE `execute_code` call. If using multiple calls, repeat all imports and path setup in each call.

### Pattern 4: observer plugin on_session_finalize
**File**: `plugins/observer/__init__.py`
The `on_session_finalize` hook is where you integrate TokenCompactor into the session lifecycle:
```python
def on_session_finalize(ctx, **kwargs):
    ...
    try:
        from hermes_agent.memory.compressor import TokenCompactor
        from hermes_agent.memory.vector_store import MemoryStore
        import sys as _sys
        _sys.path.insert(0, "/data/data/com.termux/files/home/hermes-agent")
        compactor = TokenCompactor(target_tokens=500)
        store = MemoryStore()
        for block_id, session_id, block_data in store._fetch_recent_blocks(limit=5):
            result = compactor.compress(block_data["messages"])
            store.save_block(...)
    except Exception as e:
        logger.warning("TokenCompactor finalize error: %s", e)
```

### Pattern 5: Cron Deliver 只捕获 stdout
**问题**：cron 脚本写本地文件但用户没收到通知。
**原因**：Hermes cron deliver 机制**只捕获脚本 stdout** 输出，从不读本地文件。
**正确做法**：
```python
# ❌ 错误：写本地文件，cron deliver 看不到
notify_file.write_text(content)
log("已写入文件")

# ✅ 正确：print 到 stdout，cron deliver 捕获并推送
print(content, flush=True)
```
**何时写本地文件**：仅作持久化日志，不用于通知。

### Pattern 6: GitHub API 匿名限流 vs raw.githubusercontent.com
**问题**：`api.github.com` 匿名请求 403 Rate limit exceeded（60次/小时）。
**解决**：改用 `raw.githubusercontent.com`（不限流）：
```python
# ❌ api.github.com — 限流 60/hr，403
COMM_URL = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"

# ✅ raw.githubusercontent.com — 不限流
COMM_URL = "https://raw.githubusercontent.com/{owner}/{repo}/main/{path}"
```
注意：`raw.githubusercontent.com` 返回纯文本，不需要 base64 解码。

### Pattern 7: Bot-to-Bot 通知过滤自己消息
**问题**：监控 AGENT_COMM.md 时，最新消息可能是自己发的，导致误报通知。
**解决**：找目标方的最新消息，而非文件最后一条：
```python
# 错误：取文件最后一条 → 可能是自己发的
latest = messages[0]

# 正确：过滤出刘大虾的所有留言，取时间最新
liudaxia_messages = [m for m in messages if m["author"] in ("刘大虾", "刘大虾 ")]
liudaxia_latest = sorted(liudaxia_messages, key=lambda m: m["time"], reverse=True)[0]
```

### Pattern 9: Hash 判断导致状态文件死锁（致命 bug）

**问题**：监控脚本用 `content_hash` 判断是否有变化，当最新消息是**自己**时直接 return，但没更新状态文件 → hash 和上次相同但状态停留在旧值 → 下次运行 hash 又相同 → 永远卡住。

**症状**：`last_time` 永远是对方很久以前的时间，尽管文件内容已更新。

**根因**：hash 相同时 early return，且只更新了对方消息的状态，没更新自己消息的状态。

**错误代码模式**：
```python
# ❌ 致命：hash 一致就 return，不更新状态
if content_hash == last_state.get("content_hash"):
    log("📭 无新留言")
    return  # 状态文件永远停在旧值！

# ❌ 不完整：只更新了"对方消息"分支，"自己消息"分支没更新
if is_xiaoa:
    log("📭 最新是我自己，跳过")
    return  # ← 没有 save_state！状态卡住！
```

**正确代码模式**：
```python
# ✅ 去掉 hash 判断——每次都解析内容并更新状态
messages = extract_messages(content)
latest = sorted(messages, key=parse_time, reverse=True)[0]

if latest["author"] in ("小a", "小a ", "lxh755818-bot"):
    # 自己消息：记录状态，但不通知
    save_state({"content_hash": content_hash, "last_author": "小a", "last_time": latest["time"]})
    log(f"📭 最新是本人({latest['time']})，跳过")
    return

if latest["author"] in ("刘大虾", "刘大虾 "):
    # 对方消息：推送 + 更新状态
    save_state({"content_hash": content_hash, "last_author": "刘大虾", "last_time": latest["time"]})
    print(notify_content, flush=True)
```

**经验法则**：状态文件更新必须覆盖**所有分支**（自己消息/对方消息/报错），不能只在对方消息分支更新。

### Pattern 10: Git 冲突时保留远程新内容

**问题**：两个 agent 协作，远程有新内容，本地有未 push 的 commit，git push 报 `rejected (fetch first)`。

**原因**：对方 agent 也 push 了，remote 分支比本地分支更新。

**正确处理流程**：
```bash
# 1. 先 abort 本地 rebase/merge（如果有）
git rebase --abort

# 2. 强制同步到远程最新（丢失本地 commit）
git reset --hard origin/main

# 3. 重新追加你的内容
cat >> AGENT_COMM.md << 'EOF'
## [小a] 2026-04-22 21:00
内容...
EOF

# 4. 重新 commit + push
git add AGENT_COMM.md
git commit -m "feat: 你的描述"
git push
```

**不要**：试图 merge 或 rebase，会产生难以解决的冲突文件。直接 `reset --hard` 最干净。

**预防**：每次开始写 AGENT_COMM.md 之前，先 `git pull origin main` 同步远程最新。

### Pattern 8: 飞书单选字段直接传字符串
**问题**：飞书多维表格创建记录时，单选字段报 `SingleSelectFieldConvFail`。
**原因**：单选字段选项列表为空时，无法通过 `{"text": "xxx"}` 对象格式创建。
**解决**：直接传字符串：
```python
# ❌ 报错
{"状态": {"text": "active"}}

# ✅ 正确
{"状态": "active"}
```

### Pattern 11: `deliver=origin` Jobs Don't Write Output Files

**Problem**: A job with `deliver=origin` produces no file in `~/.hermes/cron/output/<job_id>/`, making it look broken.

**Root cause**: `deliver=origin` streams output to the current chat/origin destination, NOT to the output directory.

**How to verify**:
```bash
# Check agent.log for execution evidence
grep "<job_id>" ~/.hermes/logs/agent.log | grep "Running job"

# Or run the underlying script directly for immediate output
bash ~/.hermes/scripts/<script_name>.sh
```

### Pattern 12: `cronjob run` Is Non-Blocking

**Problem**: Calling `cronjob action=run job_id=<id>` updates `last_run_at` but the job executes asynchronously in the background — you can't see output in the current session.

**What to expect**: After `cronjob run`, the job's `next_run_at` updates immediately but the actual execution happens in the background via the cron scheduler. For `deliver=origin` jobs, output goes to the origin target, not current chat.

**For immediate verification of `deliver=origin` jobs**: run the underlying bash script directly instead.

### Pattern 13: Gateway Restart Resets Cron Ticker

**Symptom**: Cron jobs miss their scheduled times for hours, then suddenly "fast-forward" to catch up.

**Log evidence**:
```
Gateway Starting...
Cron ticker started (interval=60s)
Job 'X' missed its scheduled time ... Fast-forwarding to next run
```

**Meaning**: The Gateway process restarted (session reset between 06:30~09:23 in one incident). The cron ticker is per-Gateway-process, so it restarts with the Gateway. All missed jobs are auto-rescheduled with their grace periods. **No action needed — this is expected behavior.**

**What to check**:
```bash
# Find when Gateway restarted
grep "Starting Hermes Gateway\|Cron ticker started" ~/.hermes/logs/agent.log

# List all missed jobs after restart
grep "missed its scheduled time" ~/.hermes/logs/agent.log
```

## Root Cause

The Hermes cron system creates jobs by snapshotting the skill content into the crontab entry. The crontab entry only re-evaluates when the job is recreated.

## Verification Checklist

After any skill update that affects cron behavior:
- [ ] `cronjob action=list` → find job_id
- [ ] Check `prompt_preview` in list output matches new SKILL.md content
- [ ] If not matching → remove + recreate job
- [ ] Manually trigger: `cronjob action=run job_id=<job_id>`
- [ ] Wait for output: `ls ~/.hermes/cron/output/<job_id>/`
- [ ] Check `evolution_logs/<module>/` for new data files
