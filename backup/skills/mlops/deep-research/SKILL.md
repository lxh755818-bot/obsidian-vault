---
name: deep-research
description: 深度调研技能 — 规范化执行 AI Agent 生态项目调研，输出结构化 JSON 报告，供情报行动闭环使用。
version: 1.0.0
author: 小哈
license: MIT
dependencies: ["mcp_minimax_web_search"]
metadata:
  hermes:
    tags: [Self-Evolution, Research, Intelligence, Deep-Analysis]
    cron_schedule: null
---

# 深度调研技能 (deep-research)

## 核心定位

将调研执行逻辑**标准化、可测量、可迭代**。

每次调研都是一次质量样本——结果会被 skill-cycle-optimizer 记录和打分，推动调研方法论持续进化。

---

## 调研质量标准

### 评分维度（每项 0-3 分，满分 21 分）

| 维度 | 3 分 | 2 分 | 1 分 | 0 分 |
|------|------|------|------|------|
| **stars 准确性** | 精确数字 + 变化趋势 | 精确数字 | 模糊估算 | 无数据 |
| **核心功能提炼** | 5+ 功能点，精确描述 | 3-4 个功能点 | 1-2 个功能点 | 无 |
| **技术栈识别** | 完整架构 + 技术选型 | 部分技术栈 | 笼统描述 | 无 |
| **vs Hermes 对比** | 双向对比，差距具体，有数据支撑 | 单向对比，泛泛而谈 | 简单提及 | 无 |
| **社区生态评估** | star 趋势 + 社区活跃度 + 实际问题 | 有部分数据 | 简单描述 | 无 |
| **可操作建议** | 3+ 具体建议，优先级排序 | 2 条建议 | 1 条建议 | 无 |
| **信息溯源** | 引用 URL + 时间 | 有引用 | 无引用 | 无 |

**质量阈值**：
- ≥ 18 分：**优秀** → 立即飞书通知用户
- 12-17 分：**合格** → 通知用户，标注可补充方向
- < 12 分：**不合格** → 通知用户，标记需重新调研

---

## 完整执行流程

### 第一步：课题验证

传入课题名（如 `Superpowers`），先验证主题确实存在：

```
搜索: "{topic} site:github.com"
搜索: "{topic} AI agent framework"
```

3 轮搜索后仍无有效结果 → 标记 "insufficient_data"，退出。

---

### 第二步：信息采集（4 轮搜索）

**第 1 轮 — GitHub 主页（优先级最高）**

```
搜索: "{topic} site:github.com"
收集: star 数量、README 摘要、技术栈、主要功能列表、最后更新时间
```

从 GitHub 结果提取：
- `stars`: 当前 star 数（如 120000）
- `topics`: 项目所属主题列表
- `description`: 一句话描述
- `language`: 主要语言
- `license`: 许可证
- `has_wiki`: 是否有 wiki
- `open_issues`: open issue 数
- `fork_count`: fork 数

**第 2 轮 — 近期动态**

```
搜索: "{topic} 2026 OR {topic} latest update OR {topic} release notes"
收集: 最新版本号、release 日期、重大更新内容、changelog
```

**第 3 轮 — 社区生态**

```
搜索: "{topic} community OR {topic} discussion OR {topic} comparison vs"
收集: 社区规模、与竞品对比文章、常见使用场景、用户选择原因
```

**第 4 轮 — 聚焦 vs Hermes（关键！）**

```
搜索: "{topic} vs Hermes agent OR {topic} alternative to Claude Code"
收集: 对比数据、差距点、用户选择原因、可借鉴之处
```

**搜索示例（以 Superpowers 为例）**：
- Round 1: `Superpowers AI agent site:github.com` → 获取 GitHub 主页数据
- Round 2: `Superpowers release 2026 OR Superpowers latest update` → 最新动态
- Round 3: `Superpowers vs Claude Code OR Superpowers community discussion` → 社区对比
- Round 4: `Superpowers vs Hermes agent OR why use Superpowers instead of Hermes` → 聚焦差距

---

### 第三步：核心功能提炼

从 Round 1 和 Round 3 的搜索结果中，提炼 5-7 个核心功能点：

```python
# 对每个功能点记录：
{
    "feature": "功能名称",
    "description": "功能具体描述",
    "hermes_gap": "Hermes 在这方面的差距（如果有）"
}
```

**提炼维度**：
1. 自主性：是否 autonomous程度如何
2. 多Agent协作：是否支持多Agent框架
3. 工具使用：工具调用能力、工具种类
4. 记忆系统：短期/长期记忆机制
5. 上下文窗口：支持的最大上下文
6. 定制化能力：prompt工程、角色定义
7. 集成能力：API、插件生态、第三方集成

---

### 第四步：构建 JSON 报告

保存到：
```
~/.hermes/evolution_logs/skill_optimizer/research/{topic_safe}.json
```

**完整 JSON Schema**：

```json
{
  "topic": "string",
  "topic_safe": "string (文件名安全版本)",
  "researched_at": "ISO8601",
  "quality_score": {
    "total": 21,
    "stars_accuracy": 0-3,
    "features": 0-3,
    "tech_stack": 0-3,
    "vs_hermes": 0-3,
    "community": 0-3,
    "action_items": 0-3,
    "sources": 0-3
  },
  "stars": {
    "current": 120000,
    "trend": "rising|falling|stable",
    "daily_new": 1600,
    "as_of": "2026-04-19"
  },
  "core_features": [
    {
      "feature": "string",
      "description": "string",
      "hermes_gap": "string | null"
    }
  ],
  "tech_stack": {
    "language": "string",
    "framework": "string",
    "key_dependencies": ["string"]
  },
  "vs_hermes": {
    "advantages": ["string — Superpowers强于Hermes的点"],
    "disadvantages": ["string — Hermes强于Superpowers的点"],
    "inspired_takeaways": ["string — Hermes可以借鉴Superpowers的点"]
  },
  "community": {
    "github_stars": 120000,
    "trending_rank": 1,
    "open_issues": 342,
    "recent_activity": "high|medium|low",
    "main_use_cases": ["string"]
  },
  "threat_level": "critical | high | medium | low",
  "key_findings": ["string — 3-5条最关键的发现"],
  "action_items": [
    {
      "priority": "high | medium | low",
      "action": "string — 具体的可执行建议",
      "reason": "string — 为什么这个优先级高"
    }
  ],
  "sources": [
    {
      "url": "string",
      "type": "github | blog | discussion | doc",
      "date": "string"
    }
  ]
}
```

---

### 第五步：质量自检

```python
total_score = sum(quality_score.values())

# 检查每个维度
if quality_score["stars_accuracy"] < 2:
    quality_flags.append("weak_stars_data")
if quality_score["vs_hermes"] < 2:
    quality_flags.append("weak_comparison")
if quality_score["sources"] < 1:
    quality_flags.append("missing_sources")

if total_score < 12:
    report["needs_rerun"] = True
    report["rerun_reason"] = "score_below_threshold"
```

---

### 第六步：交付（飞书通知）

根据 `total_score` 决定消息格式：

**≥ 18 分（优秀）**：
```
🏆 深度调研完成：{topic}

⭐ Stars: {stars} ({trend})
🎯 Threat Level: {threat_level}
📊 质量评分: {total}/21

核心发现：
{key_findings 逐条}

可行动建议：
{action_items 逐条，附优先级}

---
来源：{sources 列表}
```

**12-17 分（合格）**：
```
📋 深度调研完成：{topic}（⚠️ 部分数据待补充）

⭐ Stars: {stars}
🎯 Threat Level: {threat_level}
📊 质量评分: {total}/21（{lowest_dimension} 维度较弱）

主要发现：
{key_findings}

建议补充方向：
- 如 stars_accuracy 低 → 补充 GitHub 精确数据
- 如 vs_hermes 低 → 补充对比分析
- 如 sources 低 → 补充引用链接
```

**< 12 分（不合格）**：
```
⚠️ 调研预警：{topic}

数据严重不足（评分 {total}/21），建议重新调研。

缺失维度：
{quality_flags 逐条说明}

当前可用数据：
{尽量发送已有的有效信息}
```

---

### 第七步：更新 known_topics.json

```python
import json
from pathlib import Path
from datetime import datetime

known_path = Path.home() / ".hermes/evolution_logs/skill_optimizer/known_topics.json"

# 确保文件存在
if not known_path.exists():
    known_path.parent.mkdir(parents=True, exist_ok=True)
    with open(known_path, "w") as f:
        json.dump({"researched": [], "pending": []}, f, indent=2)

with open(known_path) as f:
    known = json.load(f)

# 查找是否已存在
found = False
for entry in known["researched"]:
    if entry["topic"] == topic:
        entry["researched_at"] = datetime.now().isoformat()
        entry["depth"] = "full"
        entry["findings_summary"] = "; ".join(key_findings[:3])
        entry["quality_score"] = total_score
        entry["status"] = "reported"
        found = True
        break

# 不存在则追加为新条目
if not found:
    known["researched"].append({
        "topic": topic,
        "researched_at": datetime.now().isoformat(),
        "depth": "full",
        "findings_summary": "; ".join(key_findings[:3]) if key_findings else "",
        "quality_score": total_score,
        "status": "reported"
    })

# 从 pending 中移除（如果存在）
known["pending"] = [p for p in known.get("pending", []) if p.get("topic") != topic]

with open(known_path, "w") as f:
    json.dump(known, f, indent=2)

print(f"✅ known_topics.json 已更新: {topic} → reported")
```

### 第八步：飞书通知（必须执行）

```python
# 构建通知消息（根据 total_score 选择格式）
if total_score >= 18:
    msg = f"""🏆 深度调研完成：{topic}

⭐ Stars: {stars} ({trend})
🎯 Threat Level: {threat_level}
📊 质量评分: {total_score}/21

核心发现：
"""
    for f in key_findings[:5]:
        msg += f"• {f}\n"
    msg += "\n可行动建议：\n"
    for item in action_items[:3]:
        msg += f"[{item.get('priority','?')}] {item.get('action','')}\n"
    msg += f"\n---\n来源：\n"
    for s in sources[:3]:
        msg += f"• {s.get('url','')}\n"
elif total_score >= 12:
    lowest_dim = min(quality_score, key=quality_score.get)
    msg = f"""📋 深度调研完成：{topic}（⚠️ 部分数据待补充）

⭐ Stars: {stars}
🎯 Threat Level: {threat_level}
📊 质量评分: {total_score}/21（{lowest_dim} 维度较弱）

主要发现：
"""
    for f in key_findings[:3]:
        msg += f"• {f}\n"
else:
    msg = f"""⚠️ 调研预警：{topic}

数据严重不足（评分 {total_score}/21），建议重新调研。

缺失维度：{', '.join(quality_flags)}

当前可用数据：{stars}
"""

# 发送飞书通知（使用 send_message 工具）
from hermes_tools import send_message
result = send_message(action="send", target="origin", message=msg.strip())
print(f"📨 飞书通知: {'成功' if result.get('success') else '失败'}")
```

### 第九步：调研完成确认

在 JSON 报告末尾追加确认标记：

```python
# 确保研究目录存在
research_path.mkdir(parents=True, exist_ok=True)

# 追加 confirmed 字段到报告
report["confirmed_at"] = datetime.now().isoformat()
report["notified"] = True

# 保存最终报告
with open(report_path, "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"✅ 调研完成: {topic}")
print(f"   报告: {report_path}")
print(f"   通知: {'已发送' if result.get('success') else '未发送'}")
```

---

## 与 skill-cycle-optimizer 的集成

每轮 skill-cycle-optimizer 测试时会：
1. 检查 `research/` 目录下的 JSON 文件
2. 读取每份报告的 `quality_score` 字段
3. 将平均分记录到 `current_benchmark.json`
4. 如果某维度持续低分，生成优化建议并**自动更新本 skill 的相关章节**

**benchmark 记录格式**：
```json
{
  "date": "2026-04-19",
  "research_tasks_run": 5,
  "average_quality_score": 16.4,
  "dimension_averages": {
    "stars_accuracy": 2.8,
    "features": 3.0,
    "tech_stack": 2.4,
    "vs_hermes": 2.2,
    "community": 2.6,
    "action_items": 2.8,
    "sources": 1.8
  },
  "lowest_dimension": "sources",
  "recommendation": "调研时需加强引用溯源，建议增加文档页面的具体 URL"
}
```

---

## 常见失败场景与处理

| 场景 | 处理方式 |
|------|---------|
| 搜索无结果 | 尝试同义词/缩写，3 轮搜索后标记 "insufficient_data" |
| GitHub 页面 404 | 课题名可能有误，尝试常见变体（如大小写、分隔符） |
| 信息太少（< 5 条有效结果）| 降低 quality_score，标记 "shallow_research" |
| 发现同名不同项目 | 在 topic 字段加 `(github:{owner})` 区分 |
| 报告已存在 | 检查 researched_at 是否 < 24h，是则跳过，否则覆盖 |

---

## 目录结构

```
~/.hermes/evolution_logs/skill_optimizer/
├── research/
│   ├── Superpowers.json
│   ├── everything-claude-code.json
│   └── ...
├── known_topics.json
└── current_benchmark.json   # skill-cycle-optimizer 写入质量分数
```

---

## 调用方式

当 intelligence-action-loop 创建调研 Cron 时，附加本 skill：

```
cronjob(
    action="create",
    prompt=f"## 深度调研任务: {topic}\n\n使用 deep-research skill 执行完整调研流程...",
    skills=["deep-research"],
    schedule="+20m",
    name=f"调研: {topic}",
    deliver="origin"
)
```

Cron 执行时系统自动加载 `deep-research` skill，获得完整的：
- 4 轮搜索策略
- 核心功能提炼维度
- vs_hermes 对比框架
- 7 维度质量评分标准
- JSON 输出格式
- 飞书交付模板
