---
name: feishu-setup
description: 配置飞书作为 Hermes Gateway 消息平台，支持 WebSocket 长连接方式
version: 1.0.0
author: 小哈
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [Feishu, Gateway, Platform, Messaging]
---

# 飞书平台配置

## 前提条件

飞书开放平台创建企业自建应用，拿到：
- **App ID**: `cli_xxx`
- **App Secret**: `xxx`

应用需开启「机器人」能力，并申请权限（im:message, im:message.receive_v1, im:chat）

## 安装依赖

```bash
pip install lark-oapi
```

## 配置凭证

**方式1: .env 文件（推荐）**
```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_ALLOWED_USERS=*        # 或具体用户 ID，用逗号分隔
GATEWAY_ALLOW_ALL_USERS=true   # 允许所有已认证用户
```

**方式2: config.yaml**
```yaml
platforms:
  feishu:
    enabled: true
    app_id: cli_xxx
    app_secret: xxx
    domain: feishu
    connection_mode: websocket
```

## 启动 Gateway

```bash
# 在 hermes-agent 目录下
python3 -m gateway.run
```

注意：`hermes gateway run` 和 `python3 -m gateway.run` 是不同的命令，前者是 systemd 服务管理，后者是直接运行。

## 验证连接

Gateway 启动后看到以下日志表示成功：
```
[Lark] Connected in websocket mode (feishu)
[Lark] connected to wss://msg-frontier.feishu.cn/ws/v2...
```

## 群组策略配置

群聊消息受 `FEISHU_GROUP_POLICY` 控制（默认 `allowlist`）：

| 策略 | 行为 |
|------|------|
| `open` | 群里任何人 @ 机器人都响应 |
| `allowlist` | 只有白名单用户 @ 机器人才响应（默认） |
| `blacklist` | 黑名单以外的用户 @ 机器人都响应 |
| `admin_only` | 只有管理员可以 |
| `disabled` | 完全禁用群组消息 |

```bash
# 快速测试：用 open 模式（群里任何人 @ 都响应）
FEISHU_GROUP_POLICY=open

# 精确控制：用 allowlist 模式，白名单用户的 open_id 用逗号分隔
FEISHU_ALLOWED_USERS=ou_xxx,ou_yyy
FEISHU_GROUP_POLICY=allowlist

# 开放所有用户（私聊+群聊都开放）
FEISHU_ALLOWED_USERS=*
GATEWAY_ALLOW_ALL_USERS=true
```

> **注意**：`FEISHU_ALLOWED_USERS` 同时控制私聊和群组白名单。私聊无需 @，但群组必须 @ 且发送者在白名单中才会触发响应。

## 常见问题

### 群聊 @ 机器人无反应
1. 确认群里 @ 了机器人（且机器人没被禁言）
2. 检查 `FEISHU_GROUP_POLICY`——默认是 `allowlist`，需要配置白名单
3. 解决方案：临时设 `FEISHU_GROUP_POLICY=open` 测试

### 消息被拒绝 (No user allowlists configured)
设置 `FEISHU_ALLOWED_USERS=*` 或 `GATEWAY_ALLOW_ALL_USERS=true`

### lark-oapi 导入失败
确认已安装：`pip install lark-oapi`，且在 venv 中运行

### WebSocket 断开重连（正常 vs 病理）
**正常行为**：连接维持较长时间，偶尔断连后自动重连，每次重连会生成新的 `device_id`。

**病理行为（需关注）**：连接存活仅 20-30 秒就被服务器主动关闭，gateway 日志出现大量：
```
ERROR receive message loop exit, err: no close frame received or sent
INFO disconnected to wss://msg-frontier.feishu.cn/ws/v2...
INFO trying to reconnect for the Nth time
INFO connected to wss://...
```
持续循环。**可能原因**：
1. 飞书对机器人长连接有并发数/频率限制（同一账号多实例？）
2. 机器人账号存在异常行为被飞书风控
3. 飞书 WebSocket 配额耗尽（需到飞书开放平台检查应用连接数）
4. 应用发布状态变更（已发布→编辑中会导致连接被回收）

**排查步骤**：
1. 飞书开放平台 → 应用 → 连接管理，看当前在线连接数
2. 确认应用是否已发布（编辑中状态会断连）
3. 确认没有其他进程也在用同一个 bot 的 WebSocket 连接
4. 临时：停止 gateway 几分钟，让飞书清理会话，再重启
5. 若持续无法稳定连接，切换为 **Webhook 模式** 作为兜底方案

### 私聊 vs 群聊
- 私聊：直接给机器人发消息即可
- 群聊：需要 @机器人 才会触发（且发送者需在白名单/或策略为 open）

## 通过脚本发送消息（直接 HTTP API）

`lark-oapi` SDK 的消息发送 API（`client.im.v1.message.create`）builder 模式复杂且不稳定，**推荐使用 urllib 直接调用 HTTP API**：

```python
import os, json, urllib.request

# 获取凭证（从 config.yaml 的 platforms.feishu）
app_id = "cli_xxx"
app_secret = os.environ.get("FEISHU_APP_SECRET", "")

# 获取 tenant_access_token
token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
req = urllib.request.Request(token_url,
    data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
    headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=10)
token = json.loads(resp.read()).get("tenant_access_token", "")

# 发送文本消息到群组
chat_id = "oc_xxx"  # 群组 chat_id
send_url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
payload = json.dumps({
    "receive_id": chat_id,
    "msg_type": "text",
    "content": json.dumps({"text": "消息内容"})
}).encode()

req2 = urllib.request.Request(send_url, data=payload, headers={
    "Content-Type": "application/json",
    "Authorization": f"Bearer {token}"
})
resp2 = urllib.request.urlopen(req2, timeout=10)
result = json.loads(resp2.read())
# result: {"code": 0, "msg": "success"}
```

> **注意**: 需要 `im:message` 权限。`chat_id` 从 `FEISHU_HOME_CHANNEL` 配置获取，格式为 `oc_xxx`。

### ⚠️ Webhook vs API 的区别

**飞书 Webhook（`open-apis/bot/v2/hook/`）不能用**——这个是"自定义机器人" webhook，需要手动添加机器人到群并复制 token，不能用于企业自建应用 bot。尝试使用会返回 `code=19001 param invalid: incoming webhook access token invalid`。

**正确方式：tenant_access_token API**——通过 `auth/v3/tenant_access_token/internal` 获取 token，然后调用 `im/v1/messages` API。凭证来自 `config.yaml` 的 `platforms.feishu.app_id` 和 `app_secret`。

## 参考资料

- `references/feishu-websocket-reconnect-loop.md` — WebSocket 重连循环病理日志样本 + 根因分析

## 连接方式

- **WebSocket 长连接（默认）**: Hermes 主动连接飞书服务器，不需要公网 IP，但需要飞书应用已发布
- **Webhook 模式**: 需要公网 URL，飞书 POST 消息过来
