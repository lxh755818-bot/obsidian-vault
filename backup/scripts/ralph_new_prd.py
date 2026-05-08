#!/usr/bin/env python3
"""
Ralph PRD 生成器
根据需求描述，用 AI 自动生成 prd.json

Usage:
  python ralph_new_prd.py "添加任务优先级功能"
"""

import json
import sys
import re
from datetime import datetime
from pathlib import Path

RALPH_DIR = Path.home() / ".hermes" / "ralph"
OUTPUT_FILE = RALPH_DIR / "prd.json"

def slugify(text):
    """转成小写 slug"""
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text.lower()

def generate_prd(description):
    """
    根据描述生成 PRD JSON
    实际应该调用 LLM，但这里用模板 + pattern 生成基础结构
    """
    slug = slugify(description)
    date = datetime.now().strftime("%Y%m%d")
    branch = f"ralph/{slug}"

    # 基础 PRD 结构（后续可以用 AI 增强）
    prd = {
        "project": "Hermes Project",
        "branchName": branch,
        "description": description,
        "targetRepo": "",
        "userStories": [
            {
                "id": "US-001",
                "title": "需求分析与方案设计",
                "description": f"分析 {description} 的实现方案，输出技术方案文档",
                "acceptanceCriteria": [
                    "输出技术方案文档（md 文件）",
                    "包含接口设计（如果有）",
                    "包含数据结构设计",
                    "通过评审（如需要）"
                ],
                "priority": 1,
                "passes": False,
                "notes": ""
            }
        ]
    }
    return prd

def main():
    if len(sys.argv) < 2:
        print("用法: python ralph_new_prd.py <需求描述>")
        sys.exit(1)

    description = " ".join(sys.argv[1:])

    print(f"正在为需求生成 PRD: {description}")
    print("(如已有 AI 接口，这里会调用 LLM 生成更详细的 stories)")
    print()

    prd = generate_prd(description)

    # 如果用户有 AI 接口，可以在这里调用 LLM 扩展 stories
    # 目前先用模板，后续可增强

    print(f"生成 PRD:")
    print(json.dumps(prd, indent=2, ensure_ascii=False))
    print()

    # 写入文件
    confirm = input("确认写入 prd.json？(y/n): ").strip().lower()
    if confirm == "y":
        with open(OUTPUT_FILE, "w") as f:
            json.dump(prd, f, indent=2, ensure_ascii=False)
        print(f"✅ PRD 已写入 {OUTPUT_FILE}")
        print(f"   分支: {prd['branchName']}")
    else:
        print("已取消")

if __name__ == "__main__":
    main()
