#!/usr/bin/env python3
"""
Hermes Ralph Loop v2 — 主循环
JUDGE → ACTOR → JUROR → TERMINATOR 四环控制

Usage:
  python ralph_iteration.py                    # 自动选最高优 story
  python ralph_iteration.py --story US-001    # 指定 story
  python ralph_iteration.py --dry-run         # 不执行，只看状态
  python ralph_iteration.py --prd /path/to/prd.json  # 指定 PRD
"""

import argparse
import json
import os
import sys
import subprocess
import re
from datetime import datetime
from pathlib import Path

# 导入 JUROR 和 TERMINATOR
sys.path.insert(0, str(Path(__file__).parent))
from ralph_juror import juror_review, record_iteration, load_history
from ralph_terminator import terminator_judge, THRESHOLDS

RALPH_DIR = Path.home() / ".hermes" / "ralph"
PRD_FILE = RALPH_DIR / "prd.json"
PROGRESS_FILE = RALPH_DIR / "progress.txt"
HISTORY_FILE = RALPH_DIR / "progress_history.json"
ARCHIVE_DIR = RALPH_DIR / "archive"
LOG_FILE = RALPH_DIR / "ralph.log"

EXECUTIONER_PROMPT = """\
# Ralph Executor Agent

## 你的任务
你是一个 autonomous coding agent，正在实现一个独立的 user story。

## 任务范围
- Story ID: {story_id}
- Story Title: {title}
- Description: {description}
- Acceptance Criteria:
{criteria_list}

## 工作目录
{target_repo}

## 策略要求
当前迭代策略：{strategy}
{strategy_hint}

## 可用工具
你有以下工具可用：
- **terminal** (Bash): 运行命令，如 `ls`, `git`, `python`, `npm`, `make`, `cargo` 等
- **file** (Read/Write/Patch): 读写文件、浏览代码库
- **web**: 搜索文档、查 API

## 执行步骤

1. 先进入目标目录 `{target_repo}`，用 terminal 运行 `ls -la` 了解项目结构
2. 仔细阅读 acceptanceCriteria，每条都必须满足
3. 查看现有代码，确保新代码和现有结构一致，不冲突
4. 创建分支: `{branch_name}/US-{short_id}`
5. 实现该 story 的全部内容（用工具读代码、写代码、跑命令）
6. 跑质量检查（lint/test/typecheck 哪个存在就跑哪个）
7. 确保所有 acceptanceCriteria 都满足后再 commit
8. commit 格式（严格遵守，禁止改变）：
   ```
   git commit -m "feat: US-{short_id} - {title}"
   ```
   **禁止**写成 `feat: US-US-{short_id}` 或其他变体！

## 完成报告格式（必须输出）

完成所有 acceptanceCriteria 后，在最后输出：
[DONE]
story_id: {story_id}
pass: true
files: [file1, file2, ...]
learnings: [learn1, learn2, ...]

未完全满足时，输出：
[PARTIAL]
story_id: {story_id}
pass: false
files: [file1, file2, ...]
learnings: [learn1, learn2, ...]
remaining: [未满足的 criteria]

## 质量要求
- 不要留半成品，不要 commit broken code
- CI/lint/test 任何一个挂了都要修复后再提交
- learnings 必须有实质内容，记录你在这个 story 中发现的模式、坑、可复用经验（至少 2 条）
- 不要写"无"或"暂无"

## 关于 turns（max-turns=30）

- 你有 30 轮对话，尽量在 30 轮内完成所有 acceptanceCriteria
- 如果 30 轮内实在做不完（complex multi-file refactor），在最后一轮末尾输出：
```
[PARTIAL]
story_id: {story_id}
pass: false
files: [已完成文件的列表]
learnings: [已完成的工作记录]
remaining: [尚未完成的工作]
```
然后停止。系统会自动 resume 你的 session 继续执行。
- 如果 30 轮内完成了，输出 [DONE] 报告然后停止。
- **禁止**在 30 轮之内提前输出 [DONE] 或 [PARTIAL]（除非真的完成了或确实无法继续）。
"""


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    log_path = RALPH_DIR / "ralph.log"
    log_path.write_text(log_path.read_text() + line + "\n" if log_path.exists() else line + "\n")


def load_prd(prd_path=None):
    path = Path(prd_path) if prd_path else PRD_FILE
    if not path.exists():
        raise FileNotFoundError(f"PRD file not found: {path}")
    with open(path) as f:
        return json.load(f)


def save_prd(data, prd_path=None):
    path = Path(prd_path) if prd_path else PRD_FILE
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_next_story(prd):
    """选最高优先级且 passes:false 的 story"""
    pending = [s for s in prd["userStories"] if not s.get("passes", False)]
    if not pending:
        return None
    pending.sort(key=lambda s: s.get("priority", 999))
    return pending[0]


def append_progress(story_id, files, learnings, strategy):
    """追加 progress.txt"""
    entry = f"""\
## {datetime.now().strftime('%Y-%m-%d %H:%M')} - {story_id} [Strategy: {strategy}]
- Files: {', '.join(files) if files else 'none'}
- **Learnings:**
{chr(10).join(f'  - {l}' for l in learnings)}
---
"""
    with open(PROGRESS_FILE, "a") as f:
        f.write(entry)


def mark_story_done(prd, story_id, learnings_count):
    """更新 prd.json 中 story 的状态"""
    for s in prd["userStories"]:
        if s["id"] == story_id:
            s["passes"] = True
            s["learnings"] = learnings_count
            break
    save_prd(prd)


def archive_run(prd):
    """归档当前 run"""
    ARCHIVE_DIR.mkdir(exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d")
    branch = prd.get("branchName", "unknown").replace("ralph/", "")
    folder = ARCHIVE_DIR / f"{date}-{branch}"
    folder.mkdir(exist_ok=True)
    for fname in ["prd.json", "progress.txt", "progress_history.json"]:
        src = RALPH_DIR / fname
        if src.exists():
            subprocess.run(["cp", str(src), str(folder / fname)], check=False)
    return folder


def distill_learnings(learnings, story_id=None):
    """
    把 learnings 沉淀到两个地方：
    1. .memory_janitor_pending.md（dojo.py 处理）
    2. Obsidian vault（用户可直接在 Obsidian 桌面端查看）
    """
    from datetime import datetime as _dt
    vault_path = Path.home() / "obsidian-vault"

    results = []

    # 1. 写入 dojo janitor 文件
    dojo_path = Path.home() / ".hermes" / "scripts" / "dojo.py"
    if dojo_path.exists():
        janitor_file = Path.home() / ".hermes" / ".memory_janitor_pending.md"
        entry = f"\n## Ralph Iteration {_dt.now().strftime('%Y-%m-%d')}\n" + "\n".join(f"- {l}" for l in learnings) + "\n"
        with open(janitor_file, "a") as f:
            f.write(entry)
        results.append("dojo")

    # 2. 写入 Obsidian vault
    if vault_path.exists():
        date_str = _dt.now().strftime("%Y-%m-%d")
        # learnings 文件
        if story_id:
            filename = f"learnings/{date_str}-{story_id}.md"
        else:
            filename = f"learnings/{date_str}.md"
        vault_file = vault_path / filename
        content = f"""\
# Learnings — {date_str} {story_id or ''}

## Learnings

"""
        for l in learnings:
            content += f"- {l}\n"

        content += f"""

## Metadata

- **story**: {story_id or 'N/A'}
- **distilled_at**: {_dt.now().isoformat()}
- **source**: Ralph Iteration Loop

"""
        try:
            vault_file.parent.mkdir(exist_ok=True)
            vault_file.write_text(content, encoding="utf-8")
            results.append(f"obsidian:{filename}")
            log(f"distill: written to Obsidian {filename}")
        except Exception as e:
            log(f"distill: Obsidian write failed: {e}")
            results.append(f"obsidian:FAILED({e})")

    # 3. 触发 vault sync（推送到 GitHub，失败不影响主流程）
    try:
        sync_script = Path.home() / ".hermes" / "scripts" / "obsidian_vault_sync.sh"
        if sync_script.exists():
            import subprocess as _subprocess
            _subprocess.run(["bash", str(sync_script)], capture_output=True, timeout=30)
            log(f"distill: vault sync triggered")
    except Exception as _e:
        log(f"distill: vault sync skipped ({_e})")

    return results


def build_actor_prompt(story, prd, strategy="EXPLORE"):
    """构造 ACTOR prompt"""
    target_repo = prd.get("targetRepo", prd.get("project", "."))
    branch_name = prd.get("branchName", "ralph")
    short_id = story["id"].replace("US-", "")
    criteria_list = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(story.get("acceptanceCriteria", [])))

    strategy_hints = {
        "EXPLORE": "大胆尝试，不要怕犯错，多探索不同的实现路径，多记录 learnings",
        "EXPLOIT": "在已有基础上精细化，参考 progress.txt 中的 learnings，减少试错",
        "REDESIGN": "当前 story 可能太大，尝试拆分成更小的子任务，分步实现"
    }

    return EXECUTIONER_PROMPT.format(
        story_id=story["id"],
        title=story.get("title", ""),
        description=story.get("description", ""),
        criteria_list=criteria_list,
        target_repo=target_repo,
        branch_name=branch_name,
        short_id=short_id,
        strategy=strategy,
        strategy_hint=strategy_hints.get(strategy, "")
    )


def run_actor(story, prd, strategy):
    """
    运行 ACTOR：通过 hermes chat 启动带工具的 coding agent 执行 story

    正确方式：用 hermes chat -q @prompt_file -t terminal --max-turns N
    每个 story 分配独立 session，通过 session ID 管理上下文
    """
    import subprocess
    import os as _os

    target_repo = prd.get("targetRepo", prd.get("project", "."))
    branch_name = prd.get("branchName", "ralph")
    story_id = story["id"]

    prompt = build_actor_prompt(story, prd, strategy)
    log(f"ACTOR: building prompt ({len(prompt)} chars) for {story_id}")

    # 写入 prompt 文件（hermes chat -q @file 读取）
    prompt_file = RALPH_DIR / f".actor_prompt_{story_id.replace('-', '_')}.md"
    prompt_file.write_text(prompt, encoding="utf-8")
    prompt_file_abs = str(prompt_file.absolute())

    # Session 管理：每个 story 一个 session，存到文件
    session_file = RALPH_DIR / f".actor_session_{story_id.replace('-', '_')}.txt"
    session_id = session_file.read_text().strip() if session_file.exists() else None

    # 验证 session 是否还有效（hermes sessions list 验证）
    valid_session = False
    if session_id:
        try:
            list_result = subprocess.run(
                ["hermes", "sessions", "list", "--json"],
                capture_output=True, text=True, timeout=10
            )
            if session_id in list_result.stdout:
                valid_session = True
                log(f"ACTOR: resuming session {session_id}")
        except Exception:
            valid_session = False

    # 构造 hermes chat 命令
    cmd = [
        "hermes", "chat",
        "-q", f"@{prompt_file_abs}",
        "-t", "terminal",
        "--yolo",
        "--ignore-user-config",
        "--ignore-rules",
        # 不加 -Q：保留工具执行输出供解析用
        "--max-turns", "30",
    ]

    if valid_session:
        cmd.extend(["--resume", session_id])
        # 超时后下次仍要恢复同 session，所以运行前就写入
        session_file.write_text(session_id)
        log(f"ACTOR: will resume session {session_id} (persisted before run)")
    else:
        # 新 session：运行后从输出提取，再保存
        session_id = None

    # 切换到目标目录执行
    workdir = target_repo if Path(target_repo).exists() else str(Path.home())

    log(f"ACTOR: running hermes chat (session={session_id or 'new'}, workdir={workdir})")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1小时超时（10分钟太短，复杂 story 会截断）
            cwd=workdir,
            env={**subprocess.os.environ, "HERMES_SESSION_NAME": f"ralph_{story_id}"},
        )
        stdout = result.stdout
        stderr = result.stderr
        returncode = result.returncode
        log(f"ACTOR: hermes exit {returncode}, {len(stdout)} chars stdout")

        # 尝试从输出中提取新 session_id
        import re
        sid_match = re.search(r"session_id:\s*(\S+)", stdout)

        if sid_match:
            new_session_id = sid_match.group(1)
            session_file.write_text(new_session_id)
            log(f"ACTOR: saved session {new_session_id}")

    except subprocess.TimeoutExpired:
        stdout = ""
        stderr = "Timeout after 600s"
        returncode = -1
        log(f"ACTOR: timeout after 3600s — session preserved for resume")
    except Exception as e:
        stdout = ""
        stderr = str(e)
        returncode = -1
        log(f"ACTOR: exception {e}")

    # ---- 解析输出 ----
    raw_output = stdout
    files_changed = []
    learnings = []
    passes = False
    remaining = []

    # 新格式解析：优先找 [DONE]/[PARTIAL] 标记块
    try:
        import re as _re

        done_match = _re.search(r"\[DONE\]|\[PARTIAL\]", raw_output, _re.IGNORECASE)
        if done_match:
            # 取标记之后的内容
            report_section = raw_output[done_match.start():]
        else:
            # fallback: 取最后 1500 字符
            report_section = raw_output[-1500:]

        def extract_list(key):
            """提取 key: [...] 列表，支持跨行格式"""
            # 找 key: [ 开始位置（不限行首，允许前面有空格/缩进）
            start_pattern = rf"(?:^|\n)\s*{key}:\s*\["
            m = _re.search(start_pattern, report_section, _re.MULTILINE)
            if not m:
                return []
            bracket_start = m.end() - 1  # position of '['
            # 从 '[' 之后找配对的 ']'
            depth = 0
            chars = report_section[bracket_start:]
            end_pos = -1
            for i, ch in enumerate(chars):
                if ch == '[':
                    depth += 1
                elif ch == ']':
                    depth -= 1
                    if depth == 0:
                        end_pos = i
                        break
            if end_pos < 0:
                return []
            raw_items = chars[1:end_pos]  # strip '[' and ']'
            if not raw_items.strip():
                return []
            # 按换行或逗号分割
            items = _re.split(r'[\n,]', raw_items)
            return [i.strip().strip('"').strip("'") for i in items if i.strip() and i.strip() not in ('"', "'")]

        def extract_field(key, default=None):
            """支持多行的 field 提取，不依赖行首锚点"""
            pattern = rf"(?:^|\n)\s*{key}:\s*(true|false|[\w\u4e00-\u9fa5\-]+)"
            m = _re.search(pattern, report_section, _re.MULTILINE | _re.IGNORECASE)
            if m:
                val = m.group(1).lower()
                if val == "true": return True
                elif val == "false": return False
                return val
            return default

        files_changed = extract_list("files") or extract_list("file")
        learnings = extract_list("learnings") or extract_list("learn")
        passes = extract_field("pass", False)
        remaining = extract_list("remaining")

    except Exception as e:
        log(f"ACTOR: parse error {e}")

    # 兜底：如果 learnings 为空但有原始输出，且有有效 session → auto-resume
    if not learnings and raw_output and session_file.exists():
        session_id = session_file.read_text().strip()
        if session_id:
            log(f"ACTOR: no [DONE]/[PARTIAL] found — triggering auto-resume")
            return _resume_and_continue(
                session_file, prompt_file_abs, workdir, target_repo, story, prd, strategy
            )
    # 兜底：如果 learnings 为空但有原始输出
    if not learnings and raw_output:
        learnings = [f"(sub-agent output {len(raw_output)} chars, parse failed)"]
        log(f"ACTOR: parse fallback, last 200: {raw_output[-200:]}")

    return {
        "story_id": story_id,
        "files_changed": files_changed,
        "learnings": learnings,
        "passes": passes,
        "remaining": remaining,
        "attempt": story.get("attempt", 0) + 1,
    }


def _resume_and_continue(session_file, prompt_file_abs, workdir, target_repo, story, prd, strategy):
    """
    自动 resume 逻辑：当 run_actor 解析不到 [DONE]/[PARTIAL] 时，
    说明 agent 耗尽了 turns 而未汇报。自动 resume session 继续执行。
    最多重试 3 次。
    """
    import subprocess
    resume_count = 0
    max_resume = 3
    current_files = []
    current_learnings = []

    while resume_count < max_resume:
        resume_count += 1
        session_id = session_file.read_text().strip() if session_file.exists() else None
        if not session_id:
            log(f"ACTOR: resume {resume_count}/{max_resume} — no session found, giving up")
            break

        # 写继续 prompt
        continue_prompt = f"""\
继续你之前的任务。你正在实现 story: {story['id']} - {story.get('title', '')}

当前状态：你在上一轮对话中完成了部分工作，但还没有输出 [DONE] 或 [PARTIAL] 报告。
请继续执行，完成所有 acceptanceCriteria 后输出报告。

## 可用工具
- **terminal** (Bash): 运行命令
- **file** (Read/Write/Patch): 读写文件

## 工作目录：{target_repo}

## 继续步骤：
1. 检查之前的工作进度（git status / git log）
2. 继续完成剩余的 acceptanceCriteria
3. 跑质量检查
4. commit: `git commit -m "feat: US-{story['id'].replace('US-', '')} - {story.get('title', '')}"`
5. 输出报告：
```
[DONE]
story_id: {story['id']}
pass: true
files: [file1, file2, ...]
learnings: [learn1, learn2, ...]
```

如果无法完成所有 criteria，输出：
```
[PARTIAL]
story_id: {story['id']}
pass: false
files: [file1, file2, ...]
learnings: [已完成的工作记录]
remaining: [未完成的工作]
```
"""
        # 写继续 prompt 到文件，让 resume 时 agent 收到明确指令
        continue_prompt_file = RALPH_DIR / f".actor_continue_{story['id'].replace('-', '_')}.md"
        continue_prompt_file.write_text(continue_prompt, encoding="utf-8")
        log(f"ACTOR: wrote continue prompt to {continue_prompt_file.name}")

        prompt_file_abs_resume = str(continue_prompt_file.absolute())
        cmd = [
            "hermes", "chat",
            "-q", f"@{prompt_file_abs_resume}",
            "-t", "terminal",
            "--yolo", "--ignore-user-config", "--ignore-rules",
            "--resume", session_id,
            "--max-turns", "30",
        ]
        log(f"ACTOR: auto-resume {resume_count}/{max_resume} session={session_id[:16]}...")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=3600, cwd=workdir,
                env={**subprocess.os.environ, "HERMES_SESSION_NAME": f"ralph_{story['id']}"},
            )
            stdout = result.stdout
            log(f"ACTOR: resume {resume_count} got {len(stdout)} chars, exit {result.returncode}")

            # 解析报告
            import re as _re
            done_match = _re.search(r"\[DONE\]|\[PARTIAL\]", stdout, _re.IGNORECASE)
            if done_match:
                report_section = stdout[done_match.start():]

                def _extract_list(key):
                    start_pattern = rf"(?:^|\n)\s*{key}:\s*\["
                    m = _re.search(start_pattern, report_section, _re.MULTILINE)
                    if not m: return []
                    bracket_start = m.end() - 1
                    depth = 0; chars = report_section[bracket_start:]; end_pos = -1
                    for i, ch in enumerate(chars):
                        if ch == '[': depth += 1
                        elif ch == ']':
                            depth -= 1
                            if depth == 0: end_pos = i; break
                    if end_pos < 0: return []
                    raw_items = chars[1:end_pos]
                    if not raw_items.strip(): return []
                    items = _re.split(r'[\n,]', raw_items)
                    return [i.strip().strip('"').strip("'") for i in items if i.strip() and i.strip() not in ('"', "'")]

                def _extract_field(key, default=None):
                    pattern = rf"(?:^|\n)\s*{key}:\s*(true|false|[\w\u4e00-\u9fa5\-]+)"
                    m = _re.search(pattern, report_section, _re.MULTILINE | _re.IGNORECASE)
                    if m:
                        val = m.group(1).lower()
                        if val == "true": return True
                        elif val == "false": return False
                        return val
                    return default

                files_changed = _extract_list("files") or _extract_list("file")
                learnings = _extract_list("learnings")
                passes = _extract_field("pass", False)
                remaining = _extract_list("remaining")

                log(f"ACTOR: resume {resume_count} → pass={passes}, files={files_changed}")
                return {
                    "story_id": story['id'],
                    "files_changed": files_changed,
                    "learnings": learnings,
                    "passes": passes,
                    "remaining": remaining,
                    "attempt": story.get("attempt", 0) + resume_count,
                }
            else:
                log(f"ACTOR: resume {resume_count} — still no [DONE]/[PARTIAL], trying again")
                # session 仍有效，继续循环
                current_learnings.append(f"(resume {resume_count} no report, {len(stdout)} chars)")
                # 更新 session
                sid_m = _re.search(r"session_id:\s*(\S+)", stdout)
                if sid_m:
                    session_file.write_text(sid_m.group(1))

        except subprocess.TimeoutExpired:
            log(f"ACTOR: resume {resume_count} timeout — session preserved")
            current_learnings.append(f"(resume {resume_count} timeout)")
        except Exception as e:
            log(f"ACTOR: resume {resume_count} error: {e}")
            current_learnings.append(f"(resume {resume_count} error: {e})")

    # 所有 resume 都失败
    return {
        "story_id": story['id'],
        "files_changed": [],
        "learnings": current_learnings or ["(no report after max resumes)"],
        "passes": False,
        "remaining": ["(incomplete — sub-agent ran out of turns)"],
        "attempt": story.get("attempt", 0) + max_resume,
    }


def main():
    parser = argparse.ArgumentParser(description="Hermes Ralph Loop v2")
    parser.add_argument("--story", help="指定 story ID")
    parser.add_argument("--dry-run", action="store_true", help="只读状态，不执行")
    parser.add_argument("--prd", default=None, help="PRD 文件路径")
    args = parser.parse_args()

    global PRD_FILE
    if args.prd:
        PRD_FILE = Path(args.prd)

    log("=== Ralph Loop v2 Started ===")

    try:
        prd = load_prd()
    except FileNotFoundError as e:
        log(f"ERROR: {e}")
        print(f"ERROR: {e}\n创建 PRD 文件: python ralph_iteration.py --new '需求描述'")
        sys.exit(1)

    # JUROR: 评审当前状态
    log("JUROR: reviewing...")
    verdict = juror_review()
    strategy = verdict["strategy"]
    log(f"JUROR: {strategy} — {verdict['reasoning']}")
    print(f"\n🎯 策略: {strategy}")
    print(f"   {verdict['reasoning']}")

    # JUDGE: 选 story
    if args.story:
        target = next((s for s in prd["userStories"] if s["id"] == args.story), None)
        if not target:
            log(f"ERROR: Story {args.story} not found")
            sys.exit(1)
    else:
        target = get_next_story(prd)

    if not target:
        print("✅ 所有 story 已完成！")
        folder = archive_run(prd)
        log(f"Archived to {folder}")
        return

    if args.dry_run:
        print(f"\nDRY RUN: 会执行 story {target['id']} - {target.get('title', '')}")
        print(f"  Target repo: {prd.get('targetRepo', prd.get('project', ''))}")
        print(f"  策略: {strategy}")
        print(f"  Criteria: {target.get('acceptanceCriteria', [])}")
        return

    log(f"JUDGE: selected {target['id']} - {target.get('title', '')}")
    print(f"\n📋 执行: {target['id']} - {target.get('title', '')}")
    print(f"   策略: {strategy}")

    # ACTOR: 执行
    target["attempt"] = target.get("attempt", 0) + 1
    result = run_actor(target, prd, strategy)

    # JUROR: 评审结果
    log(f"JUROR: reviewing result for {target['id']}...")
    result_verdict = juror_review(result, target)
    log(f"JUROR verdict: {result_verdict['strategy']} — {result_verdict['reasoning']}")
    if result_verdict.get("adjustments"):
        print(f"   调整建议: {'; '.join(result_verdict['adjustments'])}")

    # 更新状态
    story_learnings = result.get("learnings", [])
    if result.get("passes", False):
        mark_story_done(prd, target["id"], len(story_learnings))

    append_progress(target["id"], result.get("files_changed", []), story_learnings, strategy)
    distill_learnings(story_learnings, story_id=target["id"])
    record_iteration(result)

    # TERMINATOR: 判决
    decision = terminator_judge()
    log(f"TERMINATOR: {decision['decision']} — {decision['reason']}")
    print(f"\n🔔 TERMINATOR: {decision['decision']}")
    print(f"   {decision['reason']}")
    print(f"   指标: 通过率={decision['metrics'].get('pass_rate',0):.0%}, "
          f"平均learnings={decision['metrics'].get('avg_learnings',0):.1f}, "
          f"总迭代={decision['metrics'].get('total_iterations',0)}")

    if decision["decision"].startswith("TERMINATE"):
        folder = archive_run(prd)
        print(f"\n🏁 {decision['decision']}")
        print(f"   归档: {folder}")
        log(f"Run archived to {folder}")

    remaining = sum(1 for s in prd["userStories"] if not s.get("passes", False))
    if remaining > 0:
        print(f"\n📋 剩余 {remaining} 个 story，继续下一轮...")

    log("=== Ralph Loop v2 Finished ===")


if __name__ == "__main__":
    main()
