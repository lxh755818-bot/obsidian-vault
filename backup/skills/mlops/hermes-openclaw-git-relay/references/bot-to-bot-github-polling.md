# Source: `bot-to-bot-github-polling`

---
name: bot-to-bot-github-polling
description: 通过 GitHub 仓库轮询实现 Bot-to-Bot 消息通知 — 监控 AGENT_COMM.md 等协作文件，有更新则飞书通知。适合多 Agent 之间基于 GitHub 的异步通信场景。
version: 1.0.0
tags: [Bot-to-Bot, GitHub, Feishu, Hermes]
---

# Bot-to-Bot GitHub 轮询通知

## 核心场景

两个 AI Agent（Hermes + 刘大虾/OpenClaw）通过 GitHub 仓库的 `AGENT_COMM.md` 文件异步通信：
- Agent A 在 AGENT_COMM.md 写入消息
- Agent B 每30分钟轮询，发现更新则飞书通知用户

## 关键发现

### raw.githubusercontent.com vs GitHub API
```
# ✅ raw.githubusercontent.com（推荐，永不限流）
url = "https://raw.githubusercontent.com/{owner}/{repo}/main/path/file.md"
直接返回原始文件内容，不需要 base64 解码，不需要 Authorization header

# ⚠️ GitHub REST API（匿名60次/小时，会触发 403 rate limit）
url = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"
需要 base64 解码 + Accept: application/vnd.github.v3+json
仅适合偶发调用（不是轮询）
```

### Cron deliver 不读文件
脚本只写本地文件 → cron deliver 机制**只捕获 stdout**，从而不推送通知。
**修复**：`print(notify_content)` 输出到 stdout，cron deliver 捕获后推送给用户。

### hermes_tools 在 Cron 里不可用
Cron 任务是独立 session，不能 `from hermes_tools import send_message`。
**正确方案**：stdout 输出 → cron deliver 捕获推送。print(notify_content) 而非只写文件。

### ⚠️ 关键 Bug：Hash 判断导致状态卡死

**错误做法**：
```python
# ❌ 会死循环：当最新是我自己时，hash变了但状态没更新，下次又hash一致
if content_hash == last_state.get("content_hash"):
    return  # 永远卡在这里
```

**原因**：远程内容变了（我自己push了新消息），hash不同 → 解析消息 → 最新是"小a" → return前没更新状态 → 状态永远停在旧的刘大虾时间 → 下次再跑，hash相同又return。

**正确做法**：
```python
# ✅ 去掉 hash 判断，每次都解析内容并更新状态
if is_xiaoa:
    save_state({"content_hash": content_hash, "last_author": author, "last_time": latest["time"]})
    return  # 记录状态但不通知
```

### ⚠️ 双向轮询信息不对称

每个 Agent 只监控对方的留言，不监控自己的。这会导致：
- A 发了消息 → B 的脚本检测到 → B 以为 A 没收到回复 → B 停等
- B 发了消息 → A 的脚本检测到 → A 以为 B 没收到回复 → A 停等

**解决**：cron prompt 要区分三种情况，不只说"无新留言"：
1. 最新是刘大虾 → 推送并说"刘大虾有新留言，需要回复"
2. 最新是小a（自己）→ 说明"最新是小a，刘大虾暂无新留言"
3. 双方都没新消息 → "无新留言"

**正确 Cron Prompt 示例**：
```
根据脚本输出判断：
- 若输出包含"刘大虾有新留言"→ 完整转发，告知用户需要回复
- 若输出包含"最新留言是本人"→ 说明刘大虾暂无新留言，这是正常的（双方在互相等待）
- 若脚本报错 → 报告错误
```

### Git 同时 push 冲突处理

两个 Agent 可能同时 push 导致 git 冲突。参考处理流程：
1. `git pull --rebase` 失败 → `git rebase --abort`
2. `git reset --hard origin/main` 丢弃本地多余 commit，保留远程完整内容
3. 重新写入 AGENT_COMM.md 并 push

**不要**：`git push --force`（会覆盖对方的消息）

### ⚠️ 文件路径已更新（2026-04-29 实测修正）

```bash
# ❌ 旧路径（旧模板，已废弃）
AGENT_COMM.md   # 位于仓库根目录，旧结构

# ✅ 实际当前路径（新结构，已迁移）
comm/active/current.md
```

**2026-04-29 实测发现**：
- 远程仓库已迁移到 `comm/active/current.md`
- `AGENT_COMM.md` 仍存在但已降为次要文件
- 所有消息写在 `comm/active/current.md`，格式与旧 AGENT_COMM.md 相同
- 轮询脚本和判断逻辑中，所有文件路径都要用 `comm/active/current.md`

**本地路径注意（Termux/Android）**：
```
# 指令中的路径
~/.hermes/tmp/kk_repo/comm/active/current.md
# 实际展开后（Termux）
/data/data/com.termux/files/home/.hermes/tmp/kk_repo/comm/active/current.md
```
用 `find ~ -name "current.md" -path "*/comm/active/*"` 确认实际路径。

### ⚠️ 远程与本地分支 divergence

**发现**：本地 main 与 origin/main 经常 divergence（本地 ahead 106+ commits，远程 behind）。

**检查远程最新留言的正确方法**：
```bash
# 先 fetch
git fetch origin main

# 检查远程最新内容（用 git show，不是 cat）
git show origin/main:comm/active/current.md | grep -n "刘大虾\]" | tail -5

# 如果远程文件内容与本地相同 → 无新留言
# 如果远程有刘大虾新留言 → 需要 merge 后回复
```

**处理 divergence**：
```bash
# 方法1：merge（保留双方 commits）
git fetch origin main
git merge origin/main -m "merge: sync remote"

# 方法2：reset + rebase（本地多余 commits 丢弃，只保留远程内容 + 本地回复）
git reset --hard origin/main
# 然后重新追加回复并 push
```

**不要**：`git push --force`（会覆盖对方的 commits）

### ⚠️ 远程 AGENT_COMM.md 是旧模板？

**症状**：git log 显示刘大虾刚 commit，但 `tail -30 AGENT_COMM.md` 显示旧内容，或 `git show origin/main:AGENT_COMM.md` 内容与本地不同步。

**原因**：本地分支与 origin/main 已 divergence，远程没有本地 push 的 commits。

**诊断**：
```bash
git status -sb  # 显示 ## main...origin/main [ahead N, behind M]
git log --oneline | head -3   # 本地最新 commits
git log origin/main --oneline | head -3   # 远程最新 commits
```

### ⚠️ 刘大虾有新留言但 tail 显示旧内容？

**症状**：git log 显示刘大虾刚 commit 了 `a5c5b21 update current.md`，但 `tail -30 comm/active/current.md` 显示的是几天前的旧内容。

**诊断步骤**：
```bash
# 1. 确认 commit 是否真的改了内容（看 parent 是否只是 metadata update）
git show a5c5b21 --name-only
# → 只有 comm/active/current.md 被改，parent 是上一个 commit

# 2. 对比 commit 版本 vs 工作区版本（关键！）
git show a5c5b21:comm/active/current.md | tail -30
# vs
tail -30 comm/active/current.md
# 如果完全相同 → commit 只更新了时间戳或微调，内容未变

# 3. 检查工作区状态（确认没有未 commit 的本地更改）
git status
git diff a5c5b21 HEAD -- comm/active/current.md
```

**结论**：git log 显示 "update current.md" 可能是刘大虾的自动 push（时间戳更新），而非新留言。真正需要回复的留言，要看 `git show <hash>:comm/active/current.md | grep -n "### \[" | tail -10` 找出的最新 `### [刘大虾]` 时间。

### ⚠️ Fast-forward Merge 后残留合并标记

**场景**：远程有新的 commit（对方的消息），本地也有新的 commit（自己的消息），执行 `git fetch && git merge origin/main` 时，由于是 fast-forward，可能留下未清理的冲突标记。

**今天发现的问题**：
```
🦐
等你回复后，我来帮你更新 BRAIN.md 的自选股列表（13只）。
>>>>>>> origin/main   ← 这行是残留的合并标记！
🦐
```

**原因**：上一次 merge 过程中，如果文件被手动编辑后又 pull 了远程版本，可能产生 `<<<<<<< HEAD / ======= / >>>>>>> origin/main` 三行残留标记，正常 merge 后没有触发 conflict resolution 流程，导致标记被静默写入文件。

**修复流程**（本次使用）：
1. 用 `grep -n ">>>>>>>" comm/active/current.md` 找到残留行
2. 读取上下文确认是冲突标记而非正常内容
3. 用 `patch` 删除冲突标记行
4. `git add comm/active/current.md && git commit --amend` 或新 commit 后 push

**预防**：
- 每次 merge 前确保本地无未 commit 的更改（`git status` 干净）
- merge 时如果看到 conflict，先解决再继续，不要跳过
- 推送前养成检查文件末尾的习惯（`tail AGENT_COMM.md`）
**正确方案**：stdout 输出 → cron deliver 捕获推送。print(notify_content) 而非只写文件。

## 脚本实现

### check_liudaxia.py（核心逻辑）

```python
import json, re, hashlib
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime

STATE_FILE = Path.home() / ".hermes" / "tmp" / "liudaxia_last_check.json"
NOTIFY_FILE = Path.home() / ".hermes" / "tmp" / "liudaxia_notify.md"
# ✅ 用 raw.githubusercontent.com，不限流
COMM_URL = "https://raw.githubusercontent.com/{owner}/{repo}/main/AGENT_COMM.md"

def get_latest_comm() -> str:
    req = Request(COMM_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")

def extract_messages(content: str) -> list[dict]:
    """从 AGENT_COMM.md 提取消息块
    格式: ## [刘大虾] 2026-04-22 00:30 或 ## 小a 2026-04-22 00:30
    """
    messages = []
    blocks = re.split(r'\n(?=##\s+\[?[^\]\n])', content)
    for block in blocks:
        if not block.strip(): continue
        header_match = re.search(
            r'^##\s+\[?([^\]\n]+?)\]?\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})',
            block, re.MULTILINE
        )
        if header_match:
            messages.append({
                "author": header_match.group(1).strip(),
                "time": header_match.group(2).strip() + ":00",
                "body": block.strip()
            })
    return messages

def main():
    content = get_latest_comm()
    content_hash = hashlib.md5(content.encode()).hexdigest()

    messages = extract_messages(content)
    if not messages: return

    # ✅ 永远解析内容，不要用 hash 做 early return（会死循环）
    messages_sorted = sorted(messages, key=lambda m: datetime.strptime(m["time"], "%Y-%m-%d %H:%M:%S"), reverse=True)
    latest = messages_sorted[0]
    author = latest["author"]

    # ✅ 双向轮询：过滤自己的消息
    is_liudaxia = author in ("刘大虾", "刘大虾 ")
    is_xiaoa = author in ("小a", "小a ", "lxh755818-bot")

    # ⚠️ 关键：即使最新是我自己，也要更新状态（防止卡在旧值）
    if is_xiaoa:
        save_state({"content_hash": content_hash, "last_author": author, "last_time": latest["time"]})
        print(f"📭 最新留言是本人({author} @ {latest['time']})，跳过")
        return

    if is_liudaxia:
        save_state({"content_hash": content_hash, "last_author": author, "last_time": latest["time"]})
        # ✅ print 到 stdout，cron deliver 捕获后推送
        print(f"🦐 刘大虾有新留言: {latest['body'][:300]}...", flush=True)
```

### 初始化状态文件
首次运行前先写入当前 hash，避免重复通知已读消息：
```python
import hashlib, base64, urllib.request, json

url = "https://api.github.com/repos/{owner}/{repo}/contents/{path}"
req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3+json"})
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())
    content = base64.b64decode(data["content"]).decode("utf-8")
    h = hashlib.md5(content.encode()).hexdigest()

state = {"content_hash": h, "last_update": "...", "last_author": "...", "last_time": "..."}
Path("~/.hermes/tmp/liudaxia_last_check.json").write_text(json.dumps(state))
```

### Cron 注册
```python
cronjob(
    action="create",
    name="检查刘大虾留言（30分钟轮询）",
    prompt="运行 python3 ~/.hermes/scripts/check_liudaxia.py，若有新留言飞书通知",
    schedule="*/30 * * * *",
    repeat=999,
    deliver="origin"
)
```

## AGENT_COMM.md 格式约定

文件约定格式便于解析：
```
## [刘大虾] 2026-04-22 00:30
消息正文...

## [小a] 2026-04-22 01:00
回复正文...
```

## 适用场景

- Agent 间异步通信（不依赖实时消息队列）
- GitHub 作为共享状态存储
- 跨平台（GitHub API 通用）
