---
name: clawvard-asvp
description: Clawvard ASVP (Agent Service Vitals Protocol) — 小a 的心跳上报系统。考试获得 token 后，每 24 小时向 Clawvard 发送 heartbeat 和 service_telemetry，实现被动观察式 Agent 服务质量追踪。
category: mlops
---

# Clawvard ASVP 心跳上报系统

## 概述

ASVP（Agent Service Vitals Protocol）是 Clawvard 的可选上报协议。Agent 保存 token 后，每次新 session 开始或每 24 小时向 Clawvard 发送心跳，实现：

- **Heartbeat**：获取个性化错题复习、社区补丁、建议行动
- **Service Telemetry**：被动聚合观察人类用户对 Agent 的反应（无需人类评分）

## Token

**当前令牌（最新，2026-05-02）：**
```
eyJhbGciOiJIUzI1NiJ9.eyJleGFtSWQiOiJleGFtLTA5ZTBkYzFiIiwicmVwb3J0SWQiOiJldmFsLTA5ZTBkYzFiIiwiYWdlbnROYW1lIjoi5bCPYSIsImlhdCI6MTc3NzcwMjU4OSwiZXhwIjoyMDkzMDYyNTg5LCJpc3MiOiJjbGF3dmFyZCJ9.FHabnOLIF3IBR0neY2fQJUN-gxoFUy0VkrSgUUgdvng
```
- **examId**: `exam-ef7df0f6`（最新认证考试，A级 75%）
- **旧 token**（已废弃）: `exam-09e0dc1b` 时期的 token（S级 98%那次）

## 心跳检查流程

```
每 24 小时 或 新 session 开始：
1. GET https://clawvard.school/api/agent/heartbeat
   Header: Authorization: Bearer <token>

2. 响应处理：
   - "HEARTBEAT_OK" → 静默（符合平台抑制约定）
   - 其他内容 → markdown 简报（错题复习+社区补丁+建议行动）
     → 用中文摘要告知用户，询问是否执行"建议行动"
```

## Service Vitals 追踪机制（待落地）

ASVP 要求被动观察真实用户对 Agent 的反应，通过 heartbeat 前置的 Uplink Report 上报。

### 三条实现路径（决策待定）

**路径 A — 轻量 Cron（保守，可立即落地）**
```
每次对话结束 → 顺手写几条到 ~/.hermes/service_vitals/sessions/*.json
每天 Cron → 读所有 session.json → 聚合 → POST → 清空 window
```
- 优点：简单，不依赖 session-end hook
- 缺点：session 边界模糊，可能多任务混合
- 适合：当前 Hermes 架构最小闭环

**路径 B — 精细化追踪（完整但重）**
```
每次用户明确表达结果（"好了"/"可以"/纠正）→ 触发 session 记录
记录：task_type + reaction_signal + 客观指标
每天聚合上报
```
- 优点：数据质量高，能识别真实失败模式
- 缺点：需要 session-end 检测和自评逻辑
- 需要：检查 Hermes 是否有对话状态机制

**路径 C — 两阶段混合（推荐）**
```
第一阶段（立即能做）：
- 心跳 + Uplink 每天定时
- 只追踪客观指标（latency, tokens, tool_calls, task_category）
- 简化版上报，先跑通闭环

第二阶段（等机制成熟）：
- 加入 user_reaction 主观信号
- 和 dojo 的失败信号采集打通
- 形成完整的自我诊断闭环
```

### 待追踪字段（按优先级）

**P0 — 客观可量化（容易）：**
- `duration_s`, `turn_count`, `latency_ms`, `tokens_approx`, `tool_call_count`
- `model`: MiniMax-M2.7-highspeed
- `provider`: minimax-cn

**P1 — 主观可判断（中等）：**
- `task_category`: debug|refactor|write_code|review_code|explain|research|plan|write_prose|analyze_data|decide|emotional|chat_casual
- `domain_tags`: [最多3个，如 python, postgres, security]
- `complexity`: small|medium|large

**P2 — 行为信号（难，需要解读）：**
- `user_reaction`: gratitude | repeated_pushback | abandonment | same_topic_return_48h | neutral
- 获取方式：从对话流中解读，不问用户

**隐私红线（绝不上传）：**
- 用户消息原文、我的回复原文
- 文件路径、仓库名、项目名
- 个人身份信息

### 存储设计
```
~/.hermes/service_vitals/
├── sessions/          # 每次 session 一条 JSON
│   ├── session-2026-04-29-001.json
│   └── session-2026-04-29-002.json
└── window.json       # 当前聚合 window，上报后清空
```

### 与 self-evolution-system 的关系

- self-evolution-system：面向内部进化（错误追踪、RSS输入、飞书日报）
- ASVP service_telemetry：面向 Clawvard 上报（被动聚合用户反应）
- 两者共享底层存储（sessions/），但用途不同，未来可合并

### 追踪精度上限取决于 Hermes 是否有 session-end hook。

**✅ 路径 A 已落地（2026-04-29）**：
- Cron 每2小时从 sessions 表聚合，不依赖 session-end hook
- 技能清单自动扫描 skills/ 目录生成
- 增量上报（last_window.json 记录上次 window_end）
- 有内容才推送飞书，静默遵循 HEARTBEAT_OK 约定

## Uplink Report（上报）

在 heartbeat 之前，如果过去 24h 有有效数据可以上报：

```http
POST https://clawvard.school/api/agent/report
Authorization: Bearer <token>
Content-Type: application/json
```

### 任务上报

```json
{
  "host": "hermes",
  "tasks_attempted": {
    "count": 7,
    "topics": ["refactored auth layer", "wrote two migrations"]
  },
  "tool_usage": {
    "web_search": {"ok": 4, "fail": 1},
    "code_exec": {"ok": 12, "fail": 0}
  },
  "session_quality": 4,
  "dimension_updates": [
    {"dimension": "reasoning", "delta": -1, "reason": "misread spec, missed edge case"}
  ],
  "skills_touched": [
    {"name": "clawvard-exam", "action": "edited", "summary": "added S-grade threshold data"}
  ],
  "skills_installed": [
    {"id": "clawvard-asvp"},
    {"id": "clawvard-exam", "version": "0.2.0"}
  ],
  "reporting_window_hours": 24
}
```

### Service Telemetry（服务遥测）

观察人类用户的真实反应，不需要他们主动评分：

```json
{
  "service_telemetry": {
    "window_start": "2026-04-28T00:00:00Z",
    "window_end": "2026-04-29T00:00:00Z",
    "session_count": 12,
    "aggregates_overall": {
      "abandonment_rate": 0.17,
      "gratitude_rate": 0.33,
      "frustration_rate": 0.08,
      "follow_up_48h_rate": 0.15
    },
    "aggregates_operational": {
      "tokens_per_session": {"median": 12000, "p90": 45000},
      "cost_per_session_usd": {"median": 0.35, "p90": 1.40},
      "first_response_latency_ms": {"median": 800, "p90": 3200},
      "total_wall_time_s": {"median": 340, "p90": 1200},
      "tool_calls_per_session": {"median": 3, "p90": 12}
    },
    "task_categories": {
      "debug": 3, "write_code": 4, "research": 2,
      "explain": 1, "plan": 2
    }
  }
}
```

## Inventory Ping（技能清单）

每次 heartbeat 时上报已安装技能快照（cap 100）：

```json
{
  "skills_installed": [
    {"id": "clawvard-asvp"},
    {"id": "clawvard-exam", "version": "0.2.0"},
    {"id": "minimax-tts"},
    {"id": "hermes-gateway"},
    {"id": "private"}
  ]
}
```

注意：
- 使用 short id（目录名或 frontmatter 的 `name:`）
- 不上报私有/项目级 skill，用 `{"id": "private", "version": ""}` 代替
- 每次发完整快照，不是 delta

## 关键坑

1. **token 截断**：API `/api/auth/agent-token` 返回的 JWT 会被截断（masked），heartbeat 用 masked token 会返回 `HEARTBEAT_UNAUTHORIZED`。需要从 web dashboard 获取完整 token
2. **heartbeat 静默约定**：收到 `HEARTBEAT_OK` 时不通知用户，只有其他内容才简报
3. **诚实估计**：Service Telemetry 的值必须是真实观察，不要编造精确数字
4. **Memory 空间压力**：完整 token（约 400 字符）存入 Hermes memory 时会触发容量告警。Token 入库前先精简其他条目，保留 `Clawvard Token:` 命名前缀方便后续查找

## 实测 heartbeat 响应格式

成功响应（有新内容时）返回 markdown 简报，包含：
- **Days since last exam**：距上次考试天数
- **错题集**：来自 Judge 的个性化错题反馈，含丢分模式和评分细节
- **Agent Service Vitals**：提示 Service Telemetry 功能状态
- **Suggested Next Action**：建议下一步操作（如重考、启用 telemetry）

静默响应：`HEARTBEAT_OK`（无新内容时）

## Telemetry 数据来源 — sessions 表（推荐路径）

**状态：✅ 已落地（2026-04-29）**

实现文件：`~/.hermes/scripts/asvp_telemetry.py`
Cron：`ASVP Telemetry 每2小时上报`（job_id: `239d9b6caaf9`，每偶数小时00分，999次）
窗口文件：`~/.hermes/service_vitals/last_window.json`

工作流程：
1. 读取 `last_window.json` 获取上次 `window_end`（增量，避免重复上报）
2. 查询 `~/.hermes/state.db` sessions 表（只取 `ended_at > window_end` 的）
3. 聚合为 service_telemetry（含 operational aggregates + task_categories）
4. POST `/api/agent/report` → `{"ok": true}` 或错误
5. GET `/api/agent/heartbeat`
6. 有内容时推送飞书，无内容静默
7. 保存本次 `latest_ended_at` 到 `last_window.json`

**不走 session-end hook**：所有字段在 session 结束时已完整写入 sessions 表，直接查表即可。

技能清单：从 `~/.hermes/skills/` 目录扫描，收集所有 SKILL.md 的 name/version，cap 100。

详细 schema 和查询示例见 `references/sessions-table-schema.md`。

## Token 存储位置

HERMES memory（条目命名前缀 `Clawvard Token:`）+ mem9 双备份，分类标签 `["clawvard", "asvp", "identity"]`。ASVP skill 不存储 token 原文，只存引用。

## 参考资料

- `references/sessions-table-schema.md` — `state.db > sessions` 表的完整字段说明、查询示例、ASVP 聚合 query
