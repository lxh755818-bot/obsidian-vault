---
name: intelligence-action-loop
description: 情报→行动闭环技能。从生态情报中提取可执行洞察，决策是否创建深度调研任务，避免重复调研，形成闭环。
version: 1.0.0
author: 小哈
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [Self-Evolution, Intelligence, Research,闭环]
    cron_schedule: null
---

# 情报行动闭环

## 核心原理

**每6轮（每12小时）情报收集后，自动执行"洞察→行动"决策**。

不产生新情报时不触发。只在 `intelligence_latest.json` 有新内容时启动闭环。

---

## 执行流程

### 第一步：读取情报

读取 `~/.hermes/evolution_logs/skill_optimizer/intelligence_latest.json`：

```python
import json
from pathlib import Path

path = Path.home() / ".hermes/evolution_logs/skill_optimizer/intelligence_latest.json"
if not path.exists():
    return  # 无情报，退出

with open(path) as f:
    intel = json.load(f)

collected_at = intel.get("collected_at", "")
insights = intel.get("insights", [])
rising = intel.get("ecosystem", {}).get("rising_stars", [])
new_entrants = intel.get("ecosystem", {}).get("new_entrants", [])
hermes = intel.get("hermes", {})
```

### 第二步：读取已知话题表

```python
known_path = Path.home() / ".hermes/evolution_logs/skill_optimizer/known_topics.json"

def load_known():
    if known_path.exists():
        with open(known_path) as f:
            return json.load(f)
    return {"researched": [], "pending": []}

def save_known(data):
    with open(known_path, "w") as f:
        json.dump(data, f, indent=2)

known = load_known()
```

**known_topics.json 结构**：
```json
{
  "researched": [
    {"topic": "GenericAgent", "researched_at": "2026-04-19T00:30:00", "depth": "full", "findings_summary": "..."},
    {"topic": "claude-mem", "researched_at": "2026-04-19T00:30:00", "depth": "brief", "findings_summary": "..."}
  ],
  "pending": [
    {"topic": "Hermes vs Superpowers gap", "created_at": "2026-04-19T00:30:00", "status": "scheduled", "cron_job_id": "abc123"}
  ]
}
```

### 第三步：洞察分类与行动决策

对每条 insights 文本进行关键词匹配，分类为：

| 类型 | 触发条件 | 行动 |
|------|---------|------|
| `new_project` | 提到新项目名（如 GenericAgent） | 创建深度调研任务 |
| `threat` | 提到"威胁"、"最大对手"、"竞争" | 创建威胁分析调研 |
| `gap` | 提到"差距"、"落后"、"需要补齐" | 创建差距研究任务 |
| `feature` | 提到具体功能/版本更新 | 可选：更新技能 |

```python
import re

# ⚠️ 必须处理混合类型：rising/new_entrants 可能包含 dict 或 str
def get_name(p):
    """统一从 dict 或 str 中提取项目名"""
    if isinstance(p, dict):
        return p.get("name", "")
    elif isinstance(p, str):
        return p
    return str(p)

def get_trend(p):
    if isinstance(p, dict):
        return p.get("trend", "")
    return ""

# 项目名提取（从 rising_stars 和 new_entrants）
known_project_names = set()
for p in rising + new_entrants:
    name = get_name(p)
    if name:
        known_project_names.add(name)

# insights 关键词检测
ACTION_RULES = [
    (r"最大威胁|威胁|竞争|对手| rivalry|threat", "threat"),
    (r"差距|落后|距离|gap|behind", "gap"),
    (r"新项目|新框架|新黑马|new entrant|new framework", "new_project"),
]

def classify_insight(text):
    for pattern, label in ACTION_RULES:
        if re.search(pattern, text, re.IGNORECASE):
            return label
    return None
```

### 第四步：决策逻辑

```python
actions = []

# 1. 新项目 → 深度调研
for p in rising + new_entrants:
    name = get_name(p)
    trend = get_trend(p)
    if name and not any(t["topic"] == name for t in known["researched"]):
        priority = "high" if any(k in str(trend).lower() for k in ["爆发", "狂飙", "王者", "第一", "增长", "trending"]) else "medium"
        actions.append({
            "type": "deep_research",
            "topic": name,
            "priority": priority,
            "reason": f"Rising: {trend}",
            "data": p if isinstance(p, dict) else {"name": name, "trend": trend}
        })

# 2. 威胁分析 → 创建威胁调研任务
for insight in insights:
    label = classify_insight(insight)
    topic_key = insight[:60]
    if label in ("threat", "gap") and not any(t["topic"] == topic_key for t in known["researched"]):
        actions.append({
            "type": "threat_analysis",
            "topic": topic_key,
            "priority": "high",
            "reason": insight,
            "data": {"insight": insight}
        })

# 去重：跳过已调研的
already_done = {a["topic"] for a in known["researched"]}
actions = [a for a in actions if a["topic"] not in already_done]
```

### 第五步：为每个行动创建 Cron 任务

```python
from hermes_tools import cronjob

for action in actions:
    topic = action["topic"]
    priority = action["priority"]

    # 构建深度调研 prompt
    # 关键：prompt 描述任务目标，具体执行完全遵循 deep-research skill 的流程
    # 不要在 prompt 里重复调研步骤，否则会和 skill 内的规范冲突
    research_prompt = f"""## 深度调研任务: {topic}

### 课题背景
{action['reason']}

### 你的角色
你是深度调研分析师。加载并严格遵循 deep-research skill 的完整方法论执行调研。

### 关键约束（来自 deep-research skill）
1. 必须执行 4 轮搜索（GitHub 主页 → 近期动态 → 社区生态 → vs Hermes）
2. 提炼 5-7 个核心功能点，每个包含 hermes_gap
3. 输出完整 JSON 报告（见 deep-research skill 的 JSON Schema）
4. 完成后必须进行质量自检，计算 quality_score 的 total 值
5. 根据质量阈值决定交付方式（≥18 优秀 / 12-17 合格 / <12 不合格）
6. 更新 known_topics.json 状态为 "reported"
7. 飞书发送摘要（deliver=origin 或调用 send_message）

### 输出要求
- JSON 必须包含 quality_score.total 字段（所有维度之和）
- stars 字段必须是精确数字或 "模糊估算"，不得为空
- sources 必须有至少 1 条引用
- 保存路径: ~/.hermes/evolution_logs/skill_optimizer/research/{topic.replace(' ', '_')}.json
"""

    # 创建一次性 Cron（deliver=origin 确保结果推送到飞书）
    # skills=["deep-research"] 确保 cron 执行时自动加载完整调研方法论
    result = cronjob(
        action="create",
        prompt=research_prompt,
        skills=["deep-research"],
        schedule="+20m",
        name=f"调研: {topic[:30]}",
        repeat=1,
        deliver="origin"
    )

    if result.get("success"):
        job_id = result.get("job", {}).get("job_id")
        known["pending"].append({
            "topic": topic,
            "created_at": datetime.now().isoformat(),
            "status": "scheduled",
            "cron_job_id": job_id,
            "action_type": action["type"]
        })
        print(f"✅ 已创建调研任务: {topic} (job_id={job_id})")
    else:
        print(f"❌ 创建失败: {topic}")
```

### 第六步：保存 known_topics

```python
save_known(known)
```

### 第七步：生成行动报告

```json
{
  "task": "intelligence_action_loop",
  "timestamp": "ISO",
  "actions_taken": N,
  "new_research_tasks": [
    {
      "topic": "GenericAgent",
      "type": "deep_research",
      "priority": "medium",
      "scheduled": true,
      "job_id": "abc123"
    }
  ],
  "skipped_duplicates": N,
  "pending_research": N
}
```

---

## 目录结构

```
~/.hermes/evolution_logs/skill_optimizer/
├── intelligence_latest.json       # 最新情报
├── known_topics.json              # 已知话题表（去重）
├── research/                       # 深度调研成果
│   ├── GenericAgent.json
│   ├── claude-mem.json
│   └── ...
├── current_benchmark.json
├── trends.json
└── state.json
```

---

## 调度集成

在 `skill-cycle-optimizer` 的 Cron job prompt 中，情报收集后自动调用本技能：

```
### 情报闭环（每6轮一次）
在情报收集完成后，如果 index % 6 == 0，执行以下步骤：
1. 调用 intelligence-action-loop 技能
2. 根据洞察创建深度调研 Cron 任务
3. 将成果追加到 trends.json 的 intelligence 字段
```

> ⚠️ **环境验证 (2026-05-04)**: `deep-research` 技能是否存在尚未确认，建议首次触发前用 `skill_view(name="deep-research")` 验证。另外 `hermes_tools.cronjob` 是内部 Python 模块，需确认在 Termux 环境下可用后再依赖。

**触发时机**：skill-cycle-optimizer 每次跑完情报收集轮后立即执行。

---

## 注意事项

- 每个话题只调研一次（`known_topics.json` 去重）
- 调研结果保存到 `research/` 子目录
- 调研任务延迟 20 分钟执行，避免和主 Cron 抢占资源
- 如果 topic 名超过50字符，截断后用作文件名
- 删除的重复话题记录到 `skipped_duplicates` 计数
