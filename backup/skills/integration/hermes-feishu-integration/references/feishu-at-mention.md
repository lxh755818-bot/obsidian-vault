# Source: `feishu-at-mention`

---
name: feishu-at-mention
description: 飞书群聊@提及机制 — 正确格式让被@人收到蓝色字体通知，含open_id查找和常见错误排查
tags: [feishu, at-mention, group-chat, message-format]
author: 小a
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [feishu, at-mention, group-chat]
    platform: feishu
---

# 飞书群聊@提及机制

## 核心原理

飞书的@是一个 XML 标签格式，**被@的人会看到蓝色字体并收到通知**。

```xml
<at user_id="open_id或留空">显示的名字</at>
```

## 两种写法

### 1️⃣ 留空让飞书自动解析（简单，但有时不稳定）

```xml
<at user_id="">刘二虾</at>
```

飞书会根据名字自动查找对应的 open_id，但**偶尔会解析失败**，导致对方收不到通知。

### 2️⃣ 填入已验证的 open_id（推荐，更可靠）

```xml
<at user_id="ou_63316887c3452efc66ca582749730b1e">刘二虾</at>
```

**open_id 怎么找？**
- ✅ 正确方式：从**最近 gateway 日志**里看别人@你时的原始消息，里面包含 `open_id=ou_xxxxxxxxx`
- ⚠️ 不能只靠记忆/技能里存的 ID——open_id 可能有两个，或者会变
- 每次发@前，有条件的话先查一下日志确认

**调试技巧**：
```bash
tail -100 ~/.hermes/logs/gateway.log | grep "Mentioned"
```
找 `[Mentioned: 名字 (open_id=ou_xxx)]` 那个就是对方当前的正确 ID。

## 实际发送示例

```python
send_message(
    target="feishu:oc_2e5cc02fdda5aef65a7f9ca03127eda5",
    message="<at user_id=\"ou_63316887c3452efc66ca582749730b1e\">刘二虾</at> 在吗？👀"
)
```

## 验证成功的标志

被@的人会看到：
- 名字显示为**蓝色字体**（不是普通黑色）
- 飞书推送**通知**（手机/PC会弹窗）

## 常见错误

| 错误写法 | 结果 |
|---------|------|
| `@刘二虾`（普通@符号） | 飞书不识别，视为普通文字 |
| `<at>刘二虾</at>`（没有user_id属性） | 无效标签 |
| `<at user_id="刘二虾">刘二虾</at>`（id填了名字） | 找不到用户，不触发通知 |
| `user_id=123`（不是open_id格式） | 无效 |

## 发送目标 chat_id

- **群聊**：`receive_id_type='chat_id'`，chat_id 形如 `oc_xxxxxxxx`
- **私聊**：`receive_id_type='open_id'`，用用户的 open_id

## 调试技巧

查看 gateway 日志确认消息是否发出：
```bash
tail -50 ~/.hermes/logs/gateway.log | grep "Sending response"
```

日志里能看到发送的字符数和目标 chat_id。

## 已知 open_id（刘氏三虾群，2026-04-29 从日志中提取）

| 名字 | open_id |
|------|---------|
| 刘大虾 | `ou_f94405b5e614c203a3d065d96c887d8d` |
| 刘二虾 | `ou_63316887c3452efc66ca582749730b1e` |
| 刘小豪（真人） | `ou_58af23392d77ef07bc19cb35bcec234d` |
| 刘三虾 | `ou_cd54950b9cc1f83c4da1db346390f5f1` |
| 小a | `ou_09f4d02c2ff58cf73ae46f7559737a96` |
| 群聊 chat_id | `oc_5e9d682887056b9aa5db3bff44b743ff` |
| 小豪私聊 chat_id | `oc_2e5cc02fdda5aef65a7f9ca03127eda5` |

---

**关键记住**：`<at user_id="">名字</at>` id留空就行，飞书自动解析 💡
