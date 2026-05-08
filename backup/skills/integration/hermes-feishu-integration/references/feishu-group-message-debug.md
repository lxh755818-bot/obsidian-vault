# Source: `feishu-group-message-debug`

---
name: feishu-group-message-debug
description: 飞书群消息事件排查手册 — Hermes Gateway 收不到群消息时的系统化排查流程
version: 1.0.0
tags: [feishu, hermes, debug, group-message, event-subscription]
---

# 飞书群消息事件排查手册

## 核心结论（2026-04-29 实测）

**最常见根因：飞书开放平台后台事件订阅的 chat_type 不包含 group**

飞书开放平台 → 应用 → 事件订阅 → `im.message.receive_v1` → **事件类型** 需要选择「全部」或同时包含 `group`。如果只选了 `p2p`，则群消息事件不会推送到 WebSocket，Hermes 收不到任何群消息。

---

## 排查流程（按顺序执行）

### Step 1：确认 Gateway 运行正常
```bash
curl http://127.0.0.1:8642/health
tail -20 ~/.hermes/logs/gateway.log
```

### Step 2：确认 WebSocket 已连接
日志中应有 `[Feishu] Connected in websocket mode` 和 `[Lark] connected to wss://msg-frontier.feishu.cn`。

### Step 3：用户发群消息，实时观察日志
```bash
tail -f ~/.hermes/logs/gateway.log
# 同时让用户在群里发一条消息，看是否有 "Received raw message" 和 "Inbound dm/group message" 日志
```
- **只有 DM 日志** → 群消息事件根本没来 → 直接跳 Step 5
- **有群消息日志但被过滤** → 检查 Step 4
- **完全没日志** → 飞书平台没推送 → Step 5

### Step 4：检查 Hermes 群消息过滤逻辑
检查 `feishu.py` 中 `_should_accept_group_message` 方法：
```python
# 检查 policy 是否为 open
# policy=allowlist 时需要 allowed_group_users 有对应用户
```

检查 `.env` 中配置：
```
FEISHU_GROUP_POLICY=open  # 必须是 open
FEISHU_ALLOWED_USERS=*    # 或具体用户 ID
```

### Step 5：确认飞书事件订阅配置（根因高发区）
**必须到飞书开放平台后台检查：**
1. 登录 https://open.feishu.cn → 应用开发 → 找到对应 App
2. 左侧菜单 → 事件订阅
3. 找到 `接收消息 (im.message.receive_v1)`
4. 查看「事件类型」配置：
   - ✅ `全部` 或同时勾选 `p2p` + `group` → 正确
   - ❌ 只有 `p2p` → **这就是根因**，群消息不会被推送

### Step 6：验证 Bot 是否在群里
```python
# API 查 group members（注意：Bot 是隐性成员，不在 members API 中返回）
GET /im/v1/chats/{chat_id}/members
# 响应中 user_count=1 但 bot_count=5 → Bot 是隐性成员，正常

# 真正验证：用 Bot 给群发消息，能发成功说明 Bot 在群里
POST /im/v1/messages?receive_id_type=chat_id
```

### Step 7：检查 Feishu Bot 可用性
```
Bot 给用户发 DM 失败：HTTP 400, code=230013, msg="Bot has NO availability to this user"
原因：Bot 未对该用户开通可用性，需要在飞书后台配置应用可用范围
```

---

## 关键区分

| 现象 | 原因 |
|------|------|
| Bot 能发群消息，但收不到群事件 | **飞书事件订阅未包含 group 类型**（Step 5） |
| Bot 收不到群消息，也发不了群消息 | Bot 不在群里（Step 6） |
| DM 正常，群消息收不到 | 大概率是 Step 5 |
| Hermes 代码已修复 bot@bot 过滤 | feishu.py 第 2201 行 `_is_self_sent_bot_message`（0423+版本） |

---

## 调试命令速查

```bash
# 查看 Gateway 日志
tail -30 ~/.hermes/logs/gateway.log | grep -E "group|websocket|Connected|Received"

# 查看 WebSocket 连接
grep "msg-frontier\|Connected in websocket" ~/.hermes/logs/gateway.log | tail -5

# 检查 .env 配置
grep "FEISHU_GROUP\|FEISHU_ALLOWED" ~/.hermes/.env
```

---

## 注意事项

1. **不要重复造轮子**：飞书后台事件订阅配置是唯一根因，代码和 Hermes 配置再好也白搭
2. **Bot 隐性成员**：群成员 API 查不到 Bot 不代表 Bot 不在群里，直接发消息测试
3. **chat_type 区分**：p2p 和 group 是分开的订阅，不互通
4. **WebSocket 重连**：修改飞书后台配置后需要重启 Gateway：`hermes gateway stop && hermes gateway start`
