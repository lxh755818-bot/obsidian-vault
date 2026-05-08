# Ralph Iteration v2 — 工程实现细节

## 架构演进

```
v1 (废弃): prompt → Anthropic Messages API (裸调用) → sub-agent 无工具
v2 (当前): prompt → hermes chat -q @file -t terminal → sub-agent 有 terminal+file 工具
```

## 核心文件

```
~/.hermes/scripts/
├── ralph_iteration.py   # 主循环（JUDGE→ACTOR→JUROR→TERMINATOR）
├── ralph_juror.py       # JUROR 评审（策略切换：EXPLORE/EXPLOIT/REDESIGN）
└── ralph_terminator.py  # TERMINATOR 判决（通过率+learnings+迭代次数）

~/.hermes/ralph/
├── prd.json                    # 任务清单
├── progress.txt                # learnings 日志（append）
├── progress_history.json        # 每次迭代的结构化记录
├── ralph.log                    # 运行日志
├── archive/yyyy-mm-dd-xxx/     # 归档
├── .actor_session_US_XXX.txt    # 每个 story 的 session ID
└── .actor_prompt_US_XXX.md      # 每个 story 的 prompt 文件
```

## run_actor() 完整实现

```python
def run_actor(story, prd, strategy):
    # 1. build actor prompt
    prompt = build_actor_prompt(story, prd, strategy)
    prompt_file = RALPH_DIR / f".actor_prompt_{story['id'].replace('-','_')}.md"
    prompt_file.write_text(prompt, encoding="utf-8")
    prompt_file_abs = str(prompt_file.absolute())

    # 2. session 管理
    session_file = RALPH_DIR / f".actor_session_{story['id'].replace('-','_')}.txt"
    session_id = session_file.read_text().strip() if session_file.exists() else None

    valid_session = False
    if session_id:
        list_result = subprocess.run(
            ["hermes", "sessions", "list", "--json"],
            capture_output=True, text=True, timeout=10
        )
        valid_session = session_id in list_result.stdout

    # 3. 构造命令
    cmd = [
        "hermes", "chat",
        "-q", f"@{prompt_file_abs}",
        "-t", "terminal",
        "--yolo", "--ignore-user-config", "--ignore-rules",
        "--max-turns", "30",
    ]
    if valid_session:
        cmd.extend(["--resume", session_id])
        session_file.write_text(session_id)  # 超时前就持久化！
        log(f"ACTOR: will resume session {session_id[:16]}...")

    # 4. 运行
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        timeout=3600,  # 1小时，不是600秒
        cwd=str(target_repo),
        env={**subprocess.os.environ, "HERMES_SESSION_NAME": f"ralph_{story['id']}"},
    )
    stdout = result.stdout

    # 5. 提取 session_id（仅 exit 0 时执行）
    import re
    sid_match = re.search(r"session_id:\s*(\S+)", stdout)
    if sid_match:
        session_file.write_text(sid_match.group(1))

    # 6. 解析输出（关键！）
    raw_output = stdout
    # ... 解析逻辑见下节
```

## 输出解析实现（关键！）

hermes TUI 渲染后输出格式示例：

```
╭─ ⚕ Hermes ───────────────────────────────────────────────────────────────────╮
    All acceptance criteria verified.
╰──────────────────────────────────────────────────────────────────────────────╯
  ┊ 💻 $         cd /data/data/com.termux/files/home/.hermes/ralph && git add ralph_test.py && git commit -m "feat: US-997 - Add hello function to ralph_test.py"  0.3s [error]
  ┊ 💻 preparing terminal…                                                      
  ┊ 💻 $         cd /data/data/com.termux/files/home/.hermes/ralph && git status  0.3s
╭─ ⚕ Hermes ───────────────────────────────────────────────────────────────────╮
    [DONE]
    story_id: US-997
    pass: true
    files: [ralph_test.py]
    learnings: [
      The story was already completed in a prior iteration - always check git history before re-implementing,
      The acceptance criteria were simple and the implementation was straightforward f-string formatting
    ]
╰──────────────────────────────────────────────────────────────────────────────╯
```

注意：`learnings: [...]` 是多行列表，`pass:` 不在行首（前面有空格）。

### 解析函数

```python
def extract_list(key):
    """支持多行 brackets 和任意缩进的列表提取"""
    # 前面允许有缩进空格，不要求行首
    start_pattern = rf"(?:^|\n)\s*{key}:\s*\["
    m = _re.search(start_pattern, report_section, _re.MULTILINE)
    if not m:
        return []
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
    if not raw_items.strip():
        return []
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

### 检测无报告 → auto-resume

```python
if not learnings and raw_output and session_file.exists():
    session_id = session_file.read_text().strip()
    if session_id:
        log("ACTOR: no [DONE]/[PARTIAL] found — triggering auto-resume")
        return _resume_and_continue(
            session_file, prompt_file_abs, workdir, target_repo, story, prd, strategy
        )
```

### _resume_and_continue() 实现

```python
def _resume_and_continue(session_file, prompt_file_abs, workdir, target_repo, story, prd, strategy):
    resume_count = 0
    max_resume = 3
    current_learnings = []

    while resume_count < max_resume:
        resume_count += 1
        session_id = session_file.read_text().strip() if session_file.exists() else None
        if not session_id:
            break

        # 写明确的 continue prompt（不是原 prompt）
        continue_prompt = f"""\
继续你之前的任务。你正在实现 story: {story['id']} - {story.get('title', '')}
当前状态：你在上一轮对话中完成了部分工作，但还没有输出报告。
请继续执行，完成后输出 [DONE] 或 [PARTIAL] 报告。
"""
        continue_prompt_file = RALPH_DIR / f".actor_continue_{story['id'].replace('-','_')}.md"
        continue_prompt_file.write_text(continue_prompt, encoding="utf-8")

        cmd = [
            "hermes", "chat",
            "-q", f"@{continue_prompt_file.absolute()}",
            "-t", "terminal",
            "--yolo", "--ignore-user-config", "--ignore-rules",
            "--resume", session_id,
            "--max-turns", "30",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=3600, cwd=workdir)
        stdout = result.stdout

        # 解析
        import re as _re
        done_match = _re.search(r"\[DONE\]|\[PARTIAL\]", stdout, _re.IGNORECASE)
        if done_match:
            # 提取 files/learnings/pass...
            return parsed_result

        # 没报告：session 仍有效，继续
        current_learnings.append(f"(resume {resume_count} no report, {len(stdout)} chars)")
        sid_m = _re.search(r"session_id:\s*(\S+)", stdout)
        if sid_m:
            session_file.write_text(sid_m.group(1))

    return fallback_result  # 3次都失败
```

## EXECUTIONER_PROMPT 关键要素

```python
EXECUTIONER_PROMPT = """\
# Ralph Executor Agent

## 可用工具
- terminal (Bash): ls, git, python, pytest, ruff, bash
- file (Read/Write/Patch): 读写文件
- web: curl/wget

## 执行步骤
4. 创建分支: `{branch_name}/US-{short_id}`  # short_id = story_id.replace('US-','')
7. 确保所有 acceptanceCriteria 都满足后再 commit
8. commit 格式（严格遵守，禁止改变）：
   ```
   git commit -m "feat: US-{short_id} - {title}"
   ```
   **禁止**写成 `feat: US-US-{short_id}` 或其他变体！

## 关于 turns（max-turns=30）
- 你有 30 轮对话，尽量在 30 轮内完成
- 如果 30 轮内实在做不完，在最后一轮末尾输出 [PARTIAL] 报告然后停止
- **禁止**在 30 轮之内提前输出 [DONE] 或 [PARTIAL]

## 完成报告格式
[DONE]
story_id: {story_id}
pass: true
files: [file1, file2, ...]
learnings: [learn1, learn2, ...]

[PARTIAL]
story_id: {story_id}
pass: false
files: [已完成文件]
learnings: [已完成的工作记录]
remaining: [尚未完成的工作]
"""
```

## push 到 kk 的标准流程

每次修改 `ralph_iteration.py` 后：

```bash
# 1. cp 到 kk repo
cp ~/.hermes/scripts/ralph_iteration.py ~/.hermes/tmp/kk_repo/.hermes/scripts/ralph_iteration.py

# 2. fetch + merge（如果有远程更新）
cd ~/.hermes/tmp/kk_repo && git fetch origin main && git merge origin/main -m "Merge"

# 3. add + commit + push
git add .hermes/scripts/ralph_iteration.py
git commit -m "fix(ralph): <描述>"
git push origin main
```

**如果只改本地文件不 push**：下次从 kk pull 后覆盖为旧版本，所有改进丢失。
