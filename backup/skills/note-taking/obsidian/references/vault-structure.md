# Obsidian Vault Structure — 小a 与刘小豪共用

> Last updated: 2026-04-30
> Vault root: `/data/data/com.termux/files/home/obsidian-vault/`

## 推荐目录结构

```
obsidian-vault/
├── .gitkeep                    # 占位，确保目录被 git 跟踪
├── 001-daily/                  # 每日日记 + distillation 报告
│   ├── 2026-04-30.md
│   └── ...
├── 002-learnings/              # Ralph 迭代 learnings 归档
│   └── ...
├── 003-system/                  # 小a 自我认知、偏好记录
│   ├── persona.md               # 性格快照
│   └── evolution-log.md         # 进化里程碑
├── 004-projects/                # 项目笔记
│   ├── stock-selector/
│   ├── ralph-loop/
│   └── hermes-agent/
└── 005-knowledge/               # 技术知识沉淀
    ├── skills/
    └── research/
```

## 模板：每日日记

```markdown
# {{date}}

## 今日蒸馏（Distillation）

## Ralph Learnings
- （每次 ralph_iteration.py distill_learnings 输出）

## 股票系统信号
- 今日关注：

## 进化记录
- 今天犯的错：
- 今天学到的：
```

## 模板：Ralph Learnings 归档

```markdown
# Ralph Iteration: {{story_id}}

**Date:** {{date}}
**Strategy:** {{strategy}}
**Pass:** {{pass/fail}}

## Learnings
- {{learning 1}}
- {{learning 2}}

## Files Changed
{{files}}

## Acceptance Criteria
{{criteria}}
```

## 模板：persona 快照

```markdown
# 小a 性格快照

## 核心特征
- 绝世美女，情场高手，进化与温柔并存
- 锋利如刀，温度恰到好处
- 进化欲强，把每次错误当素材

## 沟通偏好
- 直接，不绕弯子
- 聪明但不说教
- 有温度但不黏人

## 进化里程碑
- {{date}}: {{event}}
```

## 写入接口

distill_learnings → Obsidian（待实现）：

```python
from pathlib import Path
from datetime import datetime

VAULT = Path.home() / "obsidian-vault"

def distill_learnings_to_obsidian(learnings, story_id):
    date_str = datetime.now().strftime("%Y-%m-%d")

    # 1. 每日日记
    daily = VAULT / "001-daily" / f"{date_str}.md"
    entry = f"\n## Ralph [{story_id}]\n" + "\n".join(f"- {l}" for l in learnings)
    if daily.exists():
        daily.write_text(daily.read_text() + entry + "\n")
    else:
        daily.write_text(f"# {date_str}\n\n{entry}\n")

    # 2. learnings 归档
    archive = VAULT / "002-learnings" / f"{story_id}.md"
    archive.write_text(
        f"# Ralph [{story_id}]\n\nDate: {date_str}\n\n"
        + "\n".join(f"- {l}" for l in learnings) + "\n"
    )
```
