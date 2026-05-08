# sessions 表 — ASVP 聚合数据来源

**状态：✅ 已验证可用（2026-04-29）**

`~/.hermes/state.db` 的 `sessions` 表是 ASVP Service Telemetry 的核心数据来源，
不依赖 session-end hook，直接查询即可。

## 表结构

```sql
CREATE TABLE sessions (
    id                          TEXT PRIMARY KEY,
    source                      TEXT,          -- 'feishu' | 'cron' | 'cli'
    user_id                     TEXT,
    model                       TEXT,
    started_at                  REAL,          -- Unix timestamp
    ended_at                    REAL,          -- Unix timestamp，结束时写入
    end_reason                  TEXT,          -- 'compression' | 'cron_complete' | ...
    message_count               INTEGER,
    tool_call_count             INTEGER,
    input_tokens                INTEGER,
    output_tokens               INTEGER,
    reasoning_tokens            INTEGER,
    api_call_count              INTEGER,
    estimated_cost_usd          REAL,
    actual_cost_usd             REAL
);
```

**关键字段：**
- `ended_at IS NOT NULL` 表示 session 已结束，数据完整可用
- `input_tokens` + `output_tokens` 可直接用于 token 聚合
- `tool_call_count` 直接可用
- `source` 用于区分 feishu/cron/cli
- `end_reason` 可用于识别中断（如 `'compression'` 表示 LCM 压缩触发的正常结束）

## ASVP 聚合查询（增量）

```python
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('/data/data/com.termux/files/home/.hermes/state.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

c.execute("""
    SELECT id, source, message_count, tool_call_count,
           input_tokens, output_tokens, api_call_count,
           started_at, ended_at, end_reason
    FROM sessions
    WHERE ended_at IS NOT NULL
      AND ended_at > ?
    ORDER BY ended_at DESC
""", (last_window_end_ts,))

sessions = [dict(row) for row in c.fetchall()]
conn.close()

for s in sessions:
    s['wall_time_s'] = max(0, (s['ended_at'] or 0) - (s['started_at'] or 0))
```

## 24h 统计

```python
c.execute("""
    SELECT
        COUNT(*) as session_count,
        SUM(message_count) as total_messages,
        SUM(tool_call_count) as total_tools,
        SUM(input_tokens) as total_in_tok,
        SUM(output_tokens) as total_out_tok,
        SUM(api_call_count) as total_api,
        SUM(ended_at - started_at) as total_wall_s
    FROM sessions
    WHERE started_at > ? AND ended_at IS NOT NULL
""", (since_ts,))
```

## 按 source 分类

```python
c.execute("""
    SELECT source, COUNT(*), SUM(tool_call_count), SUM(input_tokens)
    FROM sessions
    WHERE ended_at IS NOT NULL
    GROUP BY source
""")
# feishu: 高 token 密集型对话任务
# cron:  低 token 短任务
# cli:   中等 token
```

## 与 mem9 on_session_end 的关系

**mem9 插件有 `on_session_end(messages)` 方法**，但该方法注册的 hook
`ctx.register_hook("on_session_end", ...)` **从未被 Hermes 核心调用**
（PluginContext 没有在 session 结束时触发这个 hook）。

因此 mem9 的 session-end 记忆沉淀目前不工作，但 **sessions 表在每次
session 结束时已完整写入**，所以 ASVP 聚合可以完全绕过 mem9 hook，
直接查表实现。
