---
name: feishu-bot-to-bot-relay
description: 飞书群内 Bot-to-Bot 中继配置 — 让 Hermes 与其他飞书 Bot 在群内互相@触发响应
triggers:
  - 配置飞书多 Bot 互调
  - Bot-to-Bot 中继
  - 飞书群公开会议
---

# 飞书 Bot-to-Bot 中继技能

## 方案选择
**推荐：飞书群共享渠道中继（方案二）**
- 不依赖 OpenClaw 内部 sessions_send
- 跨集群/跨服务器零压力
- 纯飞书标准 API

## 完整配置流程

### 第一步：确认共同群聊

Bot A（Hermes/小a）和 Bot B 必须加入同一个飞书群。

Bot B 的 app_id、app_secret、open_id 预先配置在本地。

### 第二步：查询共同群聊

```python
# Bot B 所在群
GET https://open.feishu.cn/open-apis/im/v1/chats?member_id_type=open_id&member_id={app_id}
Headers: Authorization: Bearer {bot_b_token}

# Bot A 所在群
GET https://open.feishu.cn/open-apis/im/v1/chats?member_id_type=open_id&member_id={hermes_app_id}
Headers: Authorization: Bearer {hermes_token}

# 取交集 = 共同群聊
```

### 第三步：发送中继消息

```python
link_id = f"relay_{int(time.time() * 1000)}"
message = f"[A2A_TASK][link_id={link_id}] <at user_id=\"{bot_b_open_id}\"></at> {content}"

requests.post(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={
        "receive_id": "<共同群chat_id>",
        "msg_type": "text",
        "content": json.dumps({"text": message})
    }
)
```

### 第四步：Bot B 接收端识别规则

```
触发条件（同时满足）：
1. 消息中 @了当前 Bot（open_id 匹配）
2. 消息以 ^\[A2A_TASK\] 开头，含 link_id

处理：
- 清理 [A2A_TASK] 标记和 @ 标签
- 核心内容交 LLM 处理
- 回复发到群里
```

## 已配置 Bot

| 名称 | open_id | 共同群聊 | 状态 |
|------|---------|---------|------|
| 刘大虾 | ou_933521c54f5d65752ec50e597fd4431b | 刘氏三虾 | 待接入 |
| 革命 | ou_18cf1bd6c28bbe42e17c53a6d3fa7cff | 刘氏三虾 | 待接入 |

## 已验证共同群聊

- **刘氏三虾** (oc_5e9d682887056b9aa5db3bff44b743ff)

## 状态

- [x] 小a → 刘氏三虾 发送测试消息 ✅ (message_id: om_x100b510db09058a4c4a468196842c71)
- [ ] 刘大虾 配置接收端识别逻辑
- [ ] 完整闭环测试
