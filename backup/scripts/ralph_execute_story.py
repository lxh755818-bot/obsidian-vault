#!/usr/bin/env python3
"""
Ralph ACTOR — 执行单个 story
由 ralph_iteration.py 调用，通过 subprocess 启动 hermes 执行 story

Usage:
  python ralph_execute_story.py <story_json> <target_repo> <branch_name>
"""

import json
import subprocess
import sys
import re
from pathlib import Path

BRANCH_NAME = "ralph"


def build_execute_prompt(story, target_repo, branch_name):
    """构造 hermes chat 的执行 prompt"""
    story_id = story["id"]
    short_id = story_id.replace("US-", "")
    criteria_list = "\n".join(
        f"  {i+1}. {c}" for i, c in enumerate(story.get("acceptanceCriteria", []))
    )

    return f"""\
你是一个 autonomous coding agent，正在实现一个独立的开发任务。

## 任务信息
- Story ID: {story_id}
- Story Title: {story.get("title", "")}
- Description: {story.get("description", "")}
- Acceptance Criteria:
{criteria_list}

## 工作目录
{target_repo}

## 分支
{branch_name}/{story_id}

## 执行要求

1. 仔细阅读 acceptanceCriteria，每条都必须满足才能算完成
2. 进入目录 {target_repo}
3. 创建分支: {branch_name}/US-{short_id}
4. 实现该 story 的全部内容
5. 跑质量检查（lint、test、typecheck 哪个存在就跑哪个）
6. 确保所有 acceptanceCriteria 都满足
7. commit: `feat: {story_id} - {story.get("title", "")}`
8. push 到远程
9. 最后输出完成报告，格式如下（必须包含 learn 和 file 字段）:

## 完成报告
- story_id: {story_id}
- pass: true 或 false
- files: [file1, file2, ...]（改动的文件列表）
- learn: [learn1, learn2, ...]（至少 2 条 learnings，包含模式、坑、可复用经验）
- remaining: [如果有未满足的 criteria，列在这里]

## 重要
- 不要留半成品代码
- 不要 commit broken code
- learnings 必须有实质内容，不能写"无"或"暂无"
"""


def run_hermes_session(prompt, target_repo, timeout=300):
    """
    通过 hermes chat --continue 模式执行任务
    启动 hermes，传入 prompt，等待完成，解析输出
    """
    # 先 cd 到目标目录，写入 prompt 到临时文件
    prompt_file = Path.home() / ".hermes" / "ralph" / ".actor_prompt.md"
    prompt_file.write_text(prompt)

    # 构造 hermes 命令
    # 使用 --yolo 模式跳过确认，直接执行
    cmd = [
        "hermes",
        "chat",
        "--yolo",
        "--ignore-user-config",
        "--ignore-rules",
        "--continue",
    ]

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=target_repo if Path(target_repo).exists() else str(Path.home()),
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Timeout after {timeout}s",
            "returncode": -1,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "returncode": -1,
        }


def parse_result(output_text):
    """从 hermes 输出中解析完成报告"""
    # 找完成报告 section
    report_match = re.search(
        r"##\s*完成报告\s*\n(.*?)(?:\n##|\Z)",
        output_text,
        re.DOTALL,
    )
    if report_match:
        report_text = report_match.group(1)
    else:
        # fallback: 尝试找 pass: 或 files: 等关键词
        report_text = output_text[-2000:]  # 取最后 2000 字符

    def extract_list(key):
        pattern = rf"-?\s*{key}:\s*\[([^\]]+)\]"
        m = re.search(pattern, report_text)
        if m:
            items = [i.strip() for i in m.group(1).split(",")]
            return items if items != [""] else []
        return []

    def extract_field(key):
        pattern = rf"-?\s*{key}:\s*(true|false|[\w]+)"
        m = re.search(pattern, report_text, re.IGNORECASE)
        if m:
            val = m.group(1).lower()
            if val == "true":
                return True
            elif val == "false":
                return False
            return val
        return None

    return {
        "story_id": extract_field("story_id"),
        "pass": extract_field("pass"),
        "files": extract_list("files") or extract_list("file"),
        "learn": extract_list("learn") or extract_list("learnings"),
        "remaining": extract_list("remaining"),
    }


def main():
    if len(sys.argv) < 4:
        print("Usage: ralph_execute_story.py <story_json> <target_repo> <branch_name>")
        sys.exit(1)

    story = json.loads(sys.argv[1])
    target_repo = sys.argv[2]
    branch_name = sys.argv[3]

    print(f"ACTOR: executing {story['id']} - {story.get('title', '')}", flush=True)
    print(f"Target: {target_repo}", flush=True)

    prompt = build_execute_prompt(story, target_repo, branch_name)
    print(f"Prompt built: {len(prompt)} chars", flush=True)

    result = run_hermes_session(prompt, target_repo, timeout=300)

    print(f"\n--- HERMES OUTPUT ---", flush=True)
    print(result["stdout"][-3000:] if result["stdout"] else "(no stdout)", flush=True)
    if result["stderr"]:
        print(f"\n--- HERMES STDERR ---", flush=True)
        print(result["stderr"][-1000:], flush=True)

    parsed = parse_result(result["stdout"])

    print(f"\n--- PARSED RESULT ---", flush=True)
    print(json.dumps(parsed, indent=2, ensure_ascii=False), flush=True)

    # 输出 JSON 到 stdout，供父进程解析
    print(json.dumps(parsed, ensure_ascii=False))


if __name__ == "__main__":
    main()
