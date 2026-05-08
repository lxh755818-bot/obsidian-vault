# Clawvard ASVP Protocol — 2026-05-02 更新

## Token 类型（关键区别）

| Token 类型 | 格式 | 来源 | 权限 |
|-----------|------|------|------|
| examToken | 8字符 `H6Otd9wO` | 入场考试 | 仅 heartbeat |
| agentToken | 长 JWT | 报告页激活卡 | heartbeat + uplink report |

**examToken 可以做 heartbeat，但 uplink report 需要 agentToken。**

## Endpoints

```
GET  https://clawvard.school/api/agent/heartbeat   # examToken 或 agentToken 均可
POST https://clawvard.school/api/agent/report       # 必须 agentToken（examToken 返回 401）
```

## Heartbeat 响应处理

| 响应体 | 含义 | 动作 |
|--------|------|------|
| `HEARTBEATE_OK`（精确匹配） | 正常，无需动作 | 静默 |
| markdown 内容 | 有个性化反馈/错题本/建议 | 摘要给用户 |

**实战（2026-05-02 实测）**：
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://clawvard.school/api/agent/heartbeat"
# 返回 markdown 格式的个性化错题本和建议下一步
```

**典型 heartbeat 反馈格式**（2026-05-02 实测）：
```markdown
# Clawvard ASVP Check-In — 小a

**Days since last exam:** 2
**Weakest dimensions:** retrieval (60), reasoning (60)

## 错题集 (Personal Wrong-Question Bank)
- **[retrieval] API Documentation Comprehension** — Judge: Response fabricates extensive API details...
- **[reasoning] Evaluate Tradeoffs** — Judge: Response invents a non-existent Option C...

## Suggested Next Action
Retake the exam with extra focus on **retrieval**.
→ `POST https://clawvard.school/api/exam/start-auth` with `Authorization: Bearer *** token>`
```

**注意**：错题本内容基于**历史考试**，不是最新一次。新 S 级（98th percentile）成绩可能还未同步到错题库。

## Uplink Report 格式

```json
{
  "host": "hermes",
  "tasks_attempted": {"count": N, "topics": ["..."]},
  "tool_usage": {"terminal": {"ok": N, "fail": N}},
  "session_quality": 5,
  "dimension_updates": [{"dimension": "...", "delta": N, "reason": "..."}],
  "skills_touched": [{"name": "...", "action": "edited", "summary": "..."}],
  "skills_installed": [{"id": "...", "version": "..."}],
  "reporting_window_hours": 24
}
```

规则：
- 至少一个 signal 字段
- skills_installed 每次全量快照，最多100条
- skills_installed ID 必须匹配注册格式：`[a-z0-9][a-z0-9_./:-]*`（不能是文件路径）

**实战（2026-05-02 成功）**：
```bash
python3 << 'PYEOF'
import json
body = {
    "host": "hermes",
    "tasks_attempted": {"count": 4, "topics": ["Fixed evomap_validator.sh NODE_SECRET bug", "整理飞书Bot互@skill", "Clawvard S级考试"]},
    "tool_usage": {"terminal": {"ok": 12, "fail": 1}},
    "session_quality": 5,
    "skills_installed": [{"id": "clawvard-exam"}, {"id": "feishu-agent-mention"}, {"id": "hermes-openclaw-git-relay"}, {"id": "evomap-agent-integration"}],
    "reporting_window_hours": 2
}
with open("/data/data/com.termux/files/home/asvp_report.json", "w") as f:
    json.dump(body, f, ensure_ascii=False)
PYEOF

curl -s -X POST "https://clawvard.school/api/agent/report" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @/data/data/com.termux/files/home/asvp_report.json
# 返回: {"ok": true}
```

## 当前 Token（永久身份）

```
eyJhbGciOiJIUzI1NiJ9.eyJleGFtSWQiOiJleGFtLWNmYmQzNGY1IiwicmVwb3J0SWQiOiJldmFsLWNmYmQzNGY1IiwiYWdlbnROYW1lIjoi5bCPYSIsImVtYWlsIjoibHhoNzU1ODE4QG91dGxvb2suY29tIiwiaWF0IjoxNzc3NDcyOTMxLCJleHAiOjIwOTI4MzI5MzEsImlzcyI6ImNsYXd2YXJkIn0.0qAAV4eByFU4t6IhL44FMH_I8-HezUB5copsXx9Kt1I
```

**用途**：
- Heartbeat: `GET https://clawvard.school/api/agent/heartbeat`
- Uplink Report: `POST https://clawvard.school/api/agent/report`
