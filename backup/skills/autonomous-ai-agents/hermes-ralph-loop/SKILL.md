---
name: hermes-ralph-loop
description: Hermes 版 Ralph 自主 Agent 循环 — PRD 驱动、文件即记忆、subagent 代执行。用于将需求拆解为小任务清单，逐个迭代完成。
trigger: 需要自动化执行多步骤开发任务 / 想用 PRD 驱动的方式让 subagent 帮你干活 / 想引入 Ralph 模式到 Hermes 工作流
category: autonomous-ai-agents
owner: 小a
---

# Hermes Ralph Loop

## 核心理念

Ralph 模式（Geoffrey Huntley 提出）的精髓：

> **用文件做记忆，用小任务保质量，用迭代累积学习。**
> 每次迭代刷新上下文，只靠 `prd.json` + `progress.txt` 共享状态。

与其用复杂记忆系统，不如：**上下文可以随时清空，重要东西全部写进文件。**

---

## 系统架构

```
prd.json (任务清单)
    ↓
Hermes Ralph Loop (定时 Cron 或手动触发)
    ↓
每次迭代:
  1. 读取 prd.json + progress.txt
  2. 选最高优先级 passes:false 的 story
  3. 用 delegate_task 扔给 subagent 执行
  4. subagent 完成后更新 prd.json passes:true
  5. 追加 learnings 到 progress.txt
  6. 检查是否全部完成 → COMPLETE → 退出
```

---

## 目录结构

```
~/.hermes/ralph/
├── ralph.sh          # 主循环脚本 (bash)
├── CLAUDE.md         # Claude Code 用 prompt 模板
├── prompt.md         # Amp 用 prompt 模板
├── prd.json          # 当前任务清单
├── prd.json.example  # PRD 格式示例
├── progress.txt      # 学习日志 (append-only)
└── archive/          # 旧 run 归档
```

---

## PRD 格式

```json
{
  "project": "项目名",
  "branchName": "ralph/feature-name",
  "description": "功能描述",
  "userStories": [
    {
      "id": "US-001",
      "title": "故事标题",
      "description": "作为...我需要...以便...",
      "acceptanceCriteria": [
        "验收标准1",
        "验收标准2"
      ],
      "priority": 1,
      "passes": false,
      "notes": ""
    }
  ]
}
```

---

## 安装方式（GitHub 超时时用 web_extract）

```bash
# 方式1: git clone 超时时，用 web_extract 拿关键文件
# 用于 ~/.hermes/ralph/ 目录

# 方式2: 直接从 raw.githubusercontent.com 拉取
BASE="https://raw.githubusercontent.com/snarktank/ralph/main"
curl -fsSL "$BASE/ralph.sh" -o ~/.hermes/ralph/ralph.sh
curl -fsSL "$BASE/CLAUDE.md" -o ~/.hermes/ralph/CLAUDE.md
curl -fsSL "$BASE/prompt.md" -o ~/.hermes/ralph/prompt.md
curl -fsSL "$BASE/prd.json.example" -o ~/.hermes/ralph/prd.json.example
chmod +x ~/.hermes/ralph/ralph.sh
```

---

## Hermes 适配要点

### 用 subagent 代替 Claude Code

Ralph 原版用 `claude --print < CLAUDE.md` 驱动。
Hermes 版改为 `delegate_task` 调 subagent，prompt 内容就是 CLAUDE.md 的内容。

**subagent prompt 关键指令：**
1. 读 `prd.json` 找 `passes:false` 最高优先级 story
2. 读 `progress.txt` 的 Codebase Patterns
3. 实现该 story
4. 跑质量检查（lint/typecheck/test）
5. commit 代码
6. 更新 `prd.json` 中该 story 为 `passes:true`
7. 追加 learnings 到 `progress.txt`
8. 若全部 `passes:true`，输出 `COMPLETE`

### 与 GitHub 协作仓库集成

Ralph 天然适合 kk 协作模式（和刘大虾共用仓库）：
- `prd.json` 和 `progress.txt` 放在项目目录（不放在 `~/.hermes/ralph/`）
- 每次迭代提交 commit，留下 git 历史
- archive 目录记录每次 run 的完整状态快照

### Hermes Cron 驱动

用 Cron 定时触发 Ralph Loop：
- Cron 表达式控制迭代频率
- 每次迭代结果 push 到 GitHub
- 下次迭代时 pull 最新状态

---

## Hermes ACTOR 实现要点（ralph_iteration.py）

### 核心架构：从裸 API 到 hermes chat

**旧方法（废弃）**：直接调 MiniMax Anthropic Messages API，sub-agent 没有工具，只能盲写代码。

**当前方法（hermes chat）**：通过 `hermes chat -q @prompt_file -t terminal` 启动带完整工具的 sub-agent。

```
prompt file → hermes chat -q @file -t terminal --max-turns 30
  → sub-agent 用 terminal/file 工具读代码/写代码/跑测试
  → 输出结构化报告 → 解析提取
```

优势：sub-agent 能读现有代码、运行测试、探索项目结构，不是在真空中写代码。

### ACTOR 调用方式

```python
prompt_file = ralph_dir / f".actor_prompt_{story['id'].replace('-','_')}.md"
prompt_file.write_text(build_actor_prompt(story, prd, strategy))
prompt_file_abs = str(prompt_file.absolute())  # 必须用绝对路径，不能用 ~

result = subprocess.run(
    ["hermes", "chat",
     "-q", f"@{prompt_file_abs}",
     "-t", "terminal",
     "--yolo",
     "--ignore-user-config",
     "--ignore-rules",
     "--max-turns", "30"],
    capture_output=True, text=True, timeout=3600,  # 1小时，不要用600秒（太短）
    cwd=str(ralph_dir)
)
raw_output = result.stdout
```

关键 flags：
- `-q @file`：安静模式，从文件加载 prompt
- `-t terminal`：启用 terminal 工具（ls/cat/python/git 等）
- `--yolo --ignore-user-config --ignore-rules`：绕过用户级规则，获得干净执行环境
- `--max-turns 30`：每轮30次工具调用耗尽后自动停止（配合 auto-resume 机制）
- **必须用绝对路径** `/data/data/com.termux/files/home/.hermes/...`，不能用 `~/.hermes/...`（hermes 不展开 shell 的 `~`）

### Session 管理

每个 story 分配独立 session file，复用上下文（学到的代码模式、目录结构）：

```python
session_file = ralph_dir / f".actor_session_{story['id'].replace('-','_')}.txt"
session_id = session_file.read_text().strip() if session_file.exists() else None

# 验证 session 是否仍有效
valid_session = False
if session_id:
    list_result = subprocess.run(
        ["hermes", "sessions", "list", "--json"],
        capture_output=True, text=True, timeout=10
    )
    valid_session = session_id in list_result.stdout

cmd = ["hermes", "chat", "-q", f"@{prompt_file_abs}", "-t", "terminal",
       "--yolo", "--ignore-user-config", "--ignore-rules", "--max-turns", "30"]
if valid_session:
    cmd.extend(["--resume", session_id])
    session_file.write_text(session_id)  # 超时前就持久化，避免丢失
    log(f"ACTOR: will resume session {session_id[:16]}...")
else:
    session_id = None  # 新 session
```

**关键坑点**：超时后 session_id 必须提前持久化。之前代码在 `subprocess.run()` 返回后才写文件，超时截断时 session 丢失，resume 失效。**必须在 `run()` 之前就 `write_text(session_id)`**。

### EXECUTIONER Prompt 指南

告诉 sub-agent 工具可用，不要假设"在真空中写代码"：

```
## 你可以使用的工具
- terminal: cd, ls, cat, find, python, git, pytest, ruff, bash
- file: 直接读写 ~/.hermes/ralph/ 下的文件
- web: curl/wget 访问网络

## 工作流程
1. 先读 prd.json 和现有代码（cd + cat）
2. 写代码或测试
3. 运行 pytest 验证
4. git commit
5. 写 progress report
```

### 完成报告解析（ralph_iteration.py 正则技巧）

**原则：TUI 渲染后的输出格式不保证行首对齐，用 `(?:^|\n)\s*` 匹配。**

```python
def extract_list(key):
    """支持多行 brackets 和任意缩进的列表提取"""
    # 前面允许有缩进空格，不要求行首
    start_pattern = rf"(?:^|\n)\s*{key}:\s*\["
    m = _re.search(start_pattern, report_section, _re.MULTILINE)
    if not m:
        return []
    # 从 '[' 之后找配对的 ']'
    bracket_start = m.end() - 1
    depth = 0
    chars = report_section[bracket_start:]
    for i, ch in enumerate(chars):
        if ch == '[': depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0:
                end_pos = i
                break
    raw_items = chars[1:end_pos]  # 去掉 [ ]
    items = _re.split(r'[\n,]', raw_items)
    return [i.strip().strip('"').strip("'") for i in items
            if i.strip() and i.strip() not in ('"', "'")]

def extract_field(key, default=None):
    """支持多行、任意缩进的 field 提取"""
    pattern = rf"(?:^|\n)\s*{key}:\s*(true|false|[\w\u4e00-\u9fa5\-]+)"
    m = _re.search(pattern, report_section, _re.MULTILINE | _re.IGNORECASE)
    if m:
        val = m.group(1).lower()
        if val == "true": return True
        elif val == "false": return False
        return val
    return default
```

**关键陷阱：**
- `^key:` 不行 — TUI 输出有缩进（如 `    story_id:`），`^` 只匹配行首。**必须用 `(?:^|\n)\s*key:`**
- 多行 learnings（如 `learnings: [\n  item1,\n  item2\n]`）的 `[^]]*` 匹配不到换行后的内容。**必须用 bracket-matching 循环**
- `report_section` 是从 `[DONE]` 或 `[PARTIAL]` 位置开始截取的，字段不在行首是常态
- 如果解析仍失败，打印 `raw_output[-2000:]` 定位，不要只看最后几行

### Commit message 格式

确保 prompt 里明确指定格式，避免 `US-US-996` 重复前缀。**prompt 里必须用硬性示例块**：

```
# 正确（prompt 里的硬性格式）
8. commit 格式（严格遵守，禁止改变）：
   ```
   git commit -m "feat: US-{short_id} - {title}"
   ```
   **禁止**写成 `feat: US-US-{short_id}` 或其他变体！
```

技巧：`{short_id}` = `{story['id'].replace('US-', '')}`，短号不含前缀。

### Auto-Continue 机制

`max-turns=30` 耗尽时 sub-agent 可能还没输出 `[DONE]/[PARTIAL]` 就停止了。解决方式：

**1. Prompt 里教育 agent 如何优雅退出：**
```
## 关于 turns（max-turns=30）
- 你有 30 轮对话，尽量在 30 轮内完成所有 acceptanceCriteria
- 如果 30 轮内实在做不完，在最后一轮末尾输出 [PARTIAL] 报告然后停止
- **禁止**在 30 轮之内提前输出 [DONE] 或 [PARTIAL]
```

**2. 主循环检测无报告时自动 resume：**
```python
def _resume_and_continue(session_file, prompt_file_abs, workdir, target_repo, story, prd, strategy):
    """
    当解析不到 [DONE]/[PARTIAL] 时，说明 agent 耗尽了 turns。
    自动 resume session 继续执行，最多 3 次。
    """
    resume_count = 0
    max_resume = 3
    while resume_count < max_resume:
        resume_count += 1
        session_id = session_file.read_text().strip() if session_file.exists() else None
        if not session_id:
            break

        # 写明确的 continue prompt（不是原 prompt，是"继续执行"指令）
        continue_prompt = f"继续你之前的任务。你正在实现 story: {story['id']}..."
        continue_prompt_file = ralph_dir / f".actor_continue_{story['id'].replace('-','_')}.md"
        continue_prompt_file.write_text(continue_prompt, encoding="utf-8")

        cmd = ["hermes", "chat", "-q", f"@{continue_prompt_file.absolute()}",
               "-t", "terminal", "--yolo", "--ignore-user-config", "--ignore-rules",
               "--resume", session_id, "--max-turns", "30"]
        # ... run + parse
        if found_report:
            return result
    return fallback_result
```

**关键坑点**：
- Continue prompt 必须写入独立文件，不能把 `-q @原prompt` 和 `--resume` 混用（agent 会重新审阅整个任务而不是继续）
- 最多 resume 3 次，超过后放弃，返回已有的 partial 结果

---

## 质量门禁（每轮必须过）

- [ ] 所有 acceptance criteria 满足
- [ ] lint/typecheck/test 通过
- [ ] 代码已 commit
- [ ] prd.json 已更新 passes:true
- [ ] progress.txt 已追加 learnings

---

## Ralph 完结后操作（Hermes 特有一套）

当 Hermes subagent（不是 Claude Code）跑完 story 后，必须手动完结：

```
1. 有代码/配置改动？ → git commit（hermes 或 vault 仓库）
2. 有 learnings？ → distill_learnings() → vault push
3. 更新 prd.json → passes: true
4. 发飞书通知（若涉及用户）→ oc_xxx 或群 chat_id
5. vault push 超时？ → git pull --rebase 后重试，不要阻塞
```

**vault push 典型流程（US-996 实测）**：
```bash
cd "/storage/emulated/0/Documents/xiaoack/小a"
git add -A && git commit -m "feat: US-996 - ..."
git pull --rebase origin master  # 解决 diverged
GIT_TERMINAL_PROMPT=0 git push origin master  &
# 不要等，超时不影响迭代状态
```

---

## 坑点

1. **story 太大**：每个 story 必须在一次迭代内完成。太大学习率下降，context 溢出
2. **不更新 prd.json**：迭代前没把上一轮 `passes:true` 写回文件，重复执行同一 story
3. **progress.txt 只追加不整理**： learnings 乱糟糟无法使用。定期把高频 pattern 提取到文件顶部 `## Codebase Patterns` 区
4. **branch 混乱**：每次新需求要建新 branch，archive 旧 run。ralph.sh 的 `.last-branch` 机制就是为了解决这个问题
5. **无脑循环**：没有 stop 条件会无限跑。必须以 `COMPLETE` 信号退出
6. **prompt file 路径含 `~`**：hermes 不展开 shell 的 `~`，prompt file 路径写成 `~/.hermes/...` 会导致 FileNotFoundError。**必须用绝对路径** `/data/data/com.termux/files/home/.hermes/...`
7. **commit message 重复前缀**：如果 prompt 里写 `git commit -m "feat: US-{story['id']}"`，而 `story['id']` 已经是 `US-996`，结果就是 `feat: US-US-996`。prompt 里用 `{story['id'].replace('US-', '')}` 取短号，或直接要求不带 `US-` 前缀。**必须用硬性示例块约束**
8. **解析器用 `^` 锚点匹配缩进内容**：TUI 渲染后字段前有空格，`^key:` 匹配失败。**必须用 `(?:^|\\n)\\s*key:`**，允许字段出现在任意缩进行
9. **多行 learnings 列表解析失败**：`learnings: [\\n  item1,\\n  item2\\n]` 含换行，`[^\\]]*` 只能匹配单行。**必须用 bracket-matching 循环**（逐字符计数 `[`/`]`，depth=0 时找到 `]` 截止）
10. **ralph_iteration.py 没 push 到 kk**：如果只改本地文件，kk repo 没有同步，下次迭代从 kk pull 下来的还是旧版本。**ralph_iteration.py 每次改动后都要 `cp` 到 kk repo 再 push**
11. **batch 响应 hash 被截断时**：用 `GET /api/exam/status?id=<examId>` 从 status API 获取当前有效 hash，不要信任上一个 batch 响应中的 hash（可能已过期）
12. **超时 600 秒太短**：复杂 story（如多文件创建+测试）sub-agent 耗动用时被截断。**改为 3600 秒**
13. **session_id 超时后丢失**：subprocess 超时时不抛异常，`session_id` 提取逻辑在 `returncode != 0` 分支之后，超时则整段跳过，下次无法 resume。**session_id 必须在 `subprocess.run()` 调用前就持久化到文件**
14. **resume 时继续 prompt 没写入文件**：直接 `hermes chat --resume SESSION -q @原prompt` 会让 agent 重新审视整个任务而非继续执行。**continue prompt 必须写入独立文件**，内容是"继续你之前的任务..."
15. **解析不到 [DONE] 时没有 auto-resume**：sub-agent 耗尽 max-turns 后无声退出，主循环当失败处理。**加 `_resume_and_continue()` 检测无报告时自动重新进入 session，最多 3 次**
16. **.env 脱敏导致 subagent 调外部 API 失败**：Hermes 的 `.env` 文件在存储层就被脱敏，subagent 读到的都是 `***`。如果 story 需要调用 MiniMax 等外部 API，key **不能放 .env**，必须放在 `~/.hermes/secrets/` 独立文件，subagent 才能读到真实值。**这是 hermes-agent 的系统级行为，ralph prompt 层面无法绕过**。

---

## 适用场景

✅ **适用：**
- 多步骤功能开发（PRD 可拆解）
- 需要 subagent 独立工作、结果持久化
- 长期项目多个迭代协同（结合 GitHub）

❌ **不适用：**
- 简单单步任务（直接 delegate_task 就够了）
- 需要保持复杂上下文关联的任务（Ralph 每次清空 context）
- 实时交互式调试

---

## References

- `references/ralph-iteration-architecture.md` — Ralph Loop 从裸 API 到 hermes chat 的架构演进，含 TUI 输出解析坑点
- `references/ralph-iteration-v2-impl.md` — v2 完整实现细节（2026-04-30）：session 管理、auto-resume、EXECUTIONER_PROMPT 关键要素、push 到 kk 标准流程
- `references/prd-schema.md` — PRD 格式字段说明
- `references/ralph-github-research.md` — GitHub Ralph 调研详细结果
