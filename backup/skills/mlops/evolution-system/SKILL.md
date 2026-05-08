---
name: evolution-system
description: Hermes 自我进化系统 - 错误追踪+知识输入+技能固化。核心循环：犯错→记录→复盘→固化。4层架构：输入→孵化→固化→输出。标签体系：facts/events/discoveries/advice。
version: 1.0.0
author: 小a
license: MIT
tags: [self-evolution, error-tracking, knowledge-management]
hermes:
  cron_schedule: "0 4 * * *"
  created: 2026-04-25
  updated: 2026-04-25
---

# 自我进化系统

## 核心循环

```
收到任务/需求
    ↓
理解层（记忆+上下文）→ 判断用什么技能
    ↓
执行层（技能+工具）→ 产出结果
    ↓
反馈层：错误？→ 立即写入 error_ledger.md（1分钟内）
    ↓
每日复盘（04:00）→ 识别重复模式（同类≥3次触发）
    ↓
评分：score = frequency × impact × auto_fix_potential
    ↓
score > 8 → 生成新skill
score 4-8 → 加入规则集
score < 4 → 归档
```

## 两条进化线

| 类型 | 触发方式 | 说明 |
|------|---------|------|
| **被动进化** | 犯错 | 错误→记录→复盘→固化 |
| **主动进化** | 每日04:00 | RSS输入→知识筛选→入库 |

## 4层架构

```
输入层（RSS/错误/用户反馈）
    ↓
孵化层（待验证的知识碎片）
    ↓
固化层（已确认的skill/规则）
    ↓
输出层（日报/周报/推送）
```

## 标签体系

- `facts` — 确认的事实/规则
- `events` — 执行过的过程/事件
- `discoveries` — 新发现/洞察
- `advice` — 经验/建议/SOP

## 文件结构

```
~/.hermes/evolution_logs/
├── error_ledger.md        # 错误记录（每次错误立即写入）
├── daily_review_YYYY-MM-DD.md  # 每日复盘报告
├── learnings/             # 知识碎片（待孵化）
│   └── rss_YYYY-MM-DD.json  # RSS原始数据
├── github_trending.json   # GitHub Trending原始数据
├── skills/               # 已固化技能
└── rules/                # 规则集（score 4-8）
```

> 参考资料：`references/cron-execution-session-0430.md` — 包含2026-04-30 cron执行完整记录、错误排查过程和RSS/Trending精选样本。

### 常见已知错误模式（2026-05-03 更新）

| 错误类型 | 出现次数 | 状态 | 备注 |
|----------|---------|------|------|
| traceback_generic | 1342+ | accepted | 日志截断，仅首行 |
| lark_ws_1011 | 12 | accepted | 飞书WebSocket心跳超时 |
| lark_ws_no_close | 40 | accepted | 飞书WebSocket无close frame |
| lark_connect_timeout | 6 | accepted | DNS/连接超时 |
| feishu_edit_failed | 7+ | accepted | 飞书消息编辑超时 |
| minimax_model_dump | 49 | accepted | `'dict' object has no attribute 'model_dump'` |
| build_anthropic_kwargs | 11 | 监控中 | 2026-05-03 新增，需观察趋势 |
| vision_invalid_source | 1 | 监控中 | 2026-05-03 新增，需观察趋势 |
| hindsight_402 | 190 | accepted | API 402 错误 |
| api_exception | 380 | accepted | 通用API异常 |

### 错误追踪文件位置

- 错误日志：`~/.hermes/logs/errors.log`
- 错误 Ledger：`~/.hermes/evolution_logs/error_ledger.md`
- 错误修正报告：`~/.hermes/evolution_logs/error_correction/YYYYMMDD_HHMMSS_report.json`
- 每日错误汇总：`~/.hermes/evolution_logs/error_correction/YYYYMMDD_HHMMSS_report.json`

**读取最近错误报告**：
```bash
ls ~/.hermes/evolution_logs/error_correction/*.json | sort | tail -3 | xargs -I{} sh -c 'echo "=== {} ===" && cat {}'
```

## 固化决策标准

| 评分 | 决策 | 说明 |
|------|------|------|
| score > 8 | 生成新skill | 高价值，值得独立skill |
| score 4-8 | 加入规则集 | 中等价值，加入 HEARTBEAT.md |
| score < 4 | 归档 | 低价值，仅记录 |

评分公式：`score = frequency × impact × auto_fix_potential`

- frequency: 出现次数（1-5）
- impact: 影响程度（1-5）
- auto_fix_potential: 自动修复可能性（0.5-2）

## 错误记录格式

```markdown
## [YYYY-MM-DD HH:MM] 错误ID: ERR-序号

### 错误描述
-

### 触发场景
-

### 根因分析
-

### 影响范围
-

### 修复记录
-

### 相关标签
#facts #events #discoveries #advice
```

### 飞书日报推送（已知问题）

**现状（2026-05-03）**：飞书推送依赖 Gateway WebSocket 长连接，Cron 任务的 `deliver` 机制负责自动路由，不需要也不应该手动调用 Feishu API。

**不要这样做**：直接用 `FeishuClient` 或 `lark-oapi` 手动发消息——凭证（Gateway App 的 app_secret）可能与 Bitable App 不同，手动调用会暴露错误的 10014 错误。

**正确做法**：Cron 报告直接输出到 stdout，`deliver` 机制会自动推送到配置的飞书地址（如 `oc_2e5cc02fdda5aef65a7f9ca03127eda5`）。不需要写推送代码。

### 飞书日报格式（4层结构）

```markdown
# 进化日报 - YYYY-MM-DD

## 一、输入层（今日新数据）
## 二、孵化层（待验证知识）
## 三、固化层（已确认的skill/规则）
## 四、输出层（日报/周报/推送）
```

- 每日04:00：evolution-review（扫描learnings，复盘进化）
- 每12小时：log-error-correction（检查错误日志）
- 每2小时：skill-cycle-optimizer（测试技能性能，保持独立）

## 每日cron执行脚本

### 脚本位置与正确调用

```bash
# ✅ 正确写法（两个脚本分开调用）
python3 ~/.hermes/scripts/rss_fetch.py
python3 ~/.hermes/scripts/github_trending.py

# ❌ 错误写法（不要合并成一行，不要加绝对路径前缀）
/data/data/com.termux/files/home/.hermes/scripts/python3 ~/.hermes/scripts/rss_fetch.py   # 错误！
```

### 输出文件位置与格式

**RSS输出**：`~/.hermes/evolution_logs/learnings/rss_YYYY-MM-DD.json`
```json
{
  "date": "2026-04-30",
  "entries": [  // 注意：是 'entries' 键，不是直接列表
    {
      "id": "oai:arXiv.org:2604.22777v1",
      "title": "...",
      "summary": "...",
      "source": "Arxiv CS.AI"  // 或 "OpenAI Blog" 等
    }
  ],
  "count": 80
}
```

**GitHub Trending输出**：`~/.hermes/evolution_logs/github_trending.json`（在同一目录，也可在 `evolution_logs/` 根目录）
```json
{
  "fetched_at": "2026-04-30T04:13:13.757668",
  "repos": [
    {
      "repo": "owner/repo",
      "url": "https://github.com/owner/repo",
      "description": "..."
    }
  ]
}
```

### 读取示例

```python
import json
# RSS
with open('~/.hermes/evolution_logs/learnings/rss_2026-04-30.json') as f:
    data = json.load(f)
entries = data['entries']  # 不是直接是list

# GitHub Trending
with open('~/.hermes/evolution_logs/github_trending.json') as f:
    data = json.load(f)
repos = data['repos']  # 不是直接是list
```

## 与skill-cycle-optimizer关系

- skill-cycle-optimizer：专注测技能性能，不负责错误追踪
- evolution-system：专注错误和知识，不重复测技能
- 两者独立，定期对比效果
