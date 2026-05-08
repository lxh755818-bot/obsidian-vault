# Source: `feishu-group-chat-debug`

---
name: feishu-group-chat-debug
description: 飞书群聊机器人不响应消息的调试方法。包含日志查看、@mention 机制解析、group_policy 解释、和常用修复方案。
version: 1.0.0
author: 小哈
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [feishu, group-chat, debugging, gateway]
    platform: feishu
---

# 飞书群聊机器人不响应消息 — 调试指南

## 查看日志

```bash
# 查看群聊相关消息（重点看是否有 inbound group message）
grep "group\|chat_type\|oc_" ~/.hermes/logs/gateway.log | tail -30

# 查看消息处理器错误
grep "processor not found\|ERROR" ~/.hermes/logs/gateway.log | tail -20

# 查看 bot 加入群的事件
grep "Bot added to chat\|bot_joined" ~/.hermes/logs/gateway.log
```

## 核心机制：飞书群聊必须 @机器人才响应

Hermes 的飞书集成在群聊中**默认需要 @机器人**才会触发响应。这个行为由 `_should_accept_group_message()` 决定：

1. 先通过 `_allow_group_message()` 检查 group_policy（open/allowlist/disabled）
2. 再检查消息是否 @了机器人（`@_all` 或 mentions 列表）

**关键代码位置：** `gateway/platforms/feishu.py` 第 3063-3080 行

### 常见误解

| 配置项 | 含义 | 是否跳过 @mention |
|--------|------|-------------------|
| `group_policy: open` | 允许所有用户发消息 | ❌ 仍然需要 @ |
| `group_policy: allowlist` | 只允许白名单用户 | ❌ 仍然需要 @ |
| `allowed_group_users` | 用户白名单 | ❌ 配合 allowlist 使用 |

**重要**：`group_policy` 控制的是"哪些用户可以发消息"，不控制"是否需要 @机器人"。

## 在群里 @机器人 的正确方式

1. 在飞书群输入框输入 `@` 选择机器人名字
2. 或者发送 `@_all`（@所有人），机器人也会响应

## 如果希望机器人无需 @ 就能响应群消息

需要修改 `_should_accept_group_message()` 的逻辑，或在 `group_rules` 中为特定群配置自定义策略。

**变通方案** — 把群 ID 加入 `group_rules`，同时把 `require_mention` 相关逻辑禁用：

在 `config.yaml` 的 `platforms.feishu` 下添加：
```yaml
group_rules:
  oc_xxxxxxxxxxxxxxxxxxxxxxxx:   # 替换为你的群 ID
    policy: open
    require_mention: false        # 需要代码支持才行，当前代码不支持此选项
```

如果需要实现"无需 @ 响应群消息"，需要修改 `gateway/platforms/feishu.py` 中 `_should_accept_group_message` 方法，添加一个 `require_mention: bool` 参数来控制。

## 检查飞书开放平台权限

如果 bot 完全收不到任何群事件，检查：
1. 开放平台 → 应用功能 → 机器人 → 已开启
2. 权限管理 → `im:message` (接收消息) → 已开通
3. 版本管理与发布 → 已发布新版本

## 确认 bot 是否在群里

### 最快方法：直接调用 Feishu API 查群成员（2026-04-29 验证）

```bash
# 1. 获取 tenant_access_token
curl -s -X POST 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d '{"app_id": "cli_a95a1e699d78dcb5", "app_secret": "你的app_secret"}'

# 2. 查询群成员
curl -s 'https://open.feishu.cn/open-apis/im/v1/chats/oc_5e9d682887056b9aa5db3bff44b743ff/members' \
  -H 'Authorization: Bearer <token>'
```

**返回 `member_total: 1` 且只有刘小豪，没有 bot 的 open_id** → 注意：`GET /im/v1/chats/{chat_id}/members` 只返回**人类用户**，不返回机器人！所以看到只有 1 人不代表 bot 不在群里。

**正确诊断方法** — 查群信息中的 `bot_count` 字段：
```bash
curl -s 'https://open.feishu.cn/open-apis/im/v1/chats/oc_5e9d682887056b9aa5db3bff44b743ff' \
  -H 'Authorization: Bearer <token>'
```
返回 `"bot_count": "5"` → 群里实际有 5 个机器人，bot 大概率已在群里。

**群消息完全收不到但 DM 正常的已知原因**：这是 OpenClaw/Hermes 的 regression bug，WebSocket 模式下群消息事件根本不推送给 bot。见 [GitHub Issue #67687](https://github.com/openclaw/openclaw/issues/67687)。

- DM 正常 ✅
- Cron 推送正常 ✅
- 群消息从未到达（连日志都没有）❌

如确认事件订阅配置正确但问题依旧 = 遇到 #67687，需等待官方修复或换用 Webhook 模式。

### 次选方法：lark-cli（需人工授权，跳过）
```bash
lark-cli auth login   # 需要浏览器授权，Termux 下可能 TTY 阻塞
lark-cli chat list-members oc_5e9d682887056b9aa5db3bff44b743ff
```

### 日志法（不推荐，消息可能根本不记录到日志）
```bash
grep "Bot added to chat\|oc_5e9d682887056b9aa5db3bff44b743ff" ~/.hermes/logs/gateway.log
```

### 权威诊断：gateway_state.json + 进程名双重确认

`gateway_state.json` 是重要参考，但**不能作为唯一依据**——进程快速重启或崩溃时，该文件可能残留旧进程状态。

```bash
# 检查 gateway_state.json（注意 updated_at 是否接近当前时间）
cat ~/.hermes/gateway_state.json

# 确认真实运行的 Gateway 进程（PID 4716 是 gateway.run，不是 hermes gateway 子进程）
ps aux | grep "python3 -m gateway.run" | grep -v grep
```

**已知的误导场景**：
- `gateway_state: draining` 但进程实际还在运行
- `gateway_state: stopped` 但 PID 文件残留导致新进程无法启动
- `gateway_state: startup_failed` 但另一个 Gateway 实例已在运行

**关键经验（2026-04-21）**：
- Termux 上 Gateway 进程名是 `python3 -m gateway.run`，不是 `hermes gateway`
- `ps aux | grep hermes` 会漏掉 gateway.run 进程
- `gateway_state.json` 的 `updated_at` 严重落后于当前时间 = 文件已过时
- 遇到 PID file race 时，先 `kill` 残留进程 + `rm ~/.hermes/gateway.pid` 再重启

## 诊断流程图

```
群里发消息 → 收不到？
  → 第一步（最快）：调用 Feishu API 查群成员
    GET /im/v1/chats/{group_id}/members
    → 只有 1 个人/没有 bot → bot 没在群里（最常见根因）
  → 第二步：检查日志有没有 group message 记录
    → 没有日志 → 飞书事件订阅问题 或 bot 权限未开通
  → 第三步：确认 group_policy 和 require_mention 配置
```
