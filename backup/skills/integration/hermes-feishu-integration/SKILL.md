---
name: hermes-feishu-integration
description: 飞书平台集成完整配置流程。包含 lark-oapi 安装、凭证配置、WebSocket 长连接启动、allowlist 设置、gateway 运行与监控、自动重启。
version: 1.1.0
author: 小哈
license: MIT
dependencies: [lark-oapi]
metadata:
  hermes:
    tags: [feishu, integration, gateway, platform, termux, android]
    platform: gateway
---

# 飞书平台集成

## 快速启动（完整流程）

```bash
cd ~/hermes-agent
source venv/bin/activate
python3 -m gateway.run
```

## 检查连接状态

```bash
ps aux | grep gateway.run | grep -v grep   # 检查进程是否存在
tail -3 ~/.hermes/logs/gateway.log          # 检查最新连接状态
```

成功连接标志：
```
INFO Lark: connected to wss://msg-frontier.feishu.cn/ws/v2
INFO gateway.platforms.feishu: [Feishu] Connected in websocket mode
```

## Gateway 进程管理

### 启动（后台运行）
```bash
cd ~/hermes-agent && source venv/bin/activate && python3 -m gateway.run >> ~/.hermes/logs/gateway.log 2>&1 &
echo "Gateway PID: $!"
```

### 检查进程
```bash
ps aux | grep "gateway.run" | grep -v grep
```

### 重启（先杀后启）
```bash
pkill -f "gateway.run" && sleep 2 && cd ~/hermes-agent && source venv/bin/activate && python3 -m gateway.run >> ~/.hermes/logs/gateway.log 2>&1 &
```

### 查看日志
```bash
tail -f ~/.hermes/logs/gateway.log
tail -f ~/.hermes/logs/agent.log
```

## Termux 开机自动启动

### 方法1：termux-boot（推荐）
1. 安装 Termux Boot：`pkg install termux-boot`
2. 创建启动脚本：
```bash
mkdir -p ~/.termux/boot/
cat > ~/.termux/boot/start-gateway.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/sh
cd /data/data/com.termux/files/home/hermes-agent
source venv/bin/activate
python3 -m gateway.run >> /data/data/com.termux/files/home/.hermes/logs/gateway.log 2>&1 &
EOF
chmod +x ~/.termux/boot/start-gateway.sh
```

### 方法2：.bashrc 启动（每次打开 Termux 自动拉起）
在 `~/.bashrc` 末尾添加：
```bash
# Auto-start Hermes Gateway
if ! pgrep -f "gateway.run" > /dev/null; then
    cd ~/hermes-agent && source venv/bin/activate && python3 -m gateway.run >> ~/.hermes/logs/gateway.log 2>&1 &
    echo "[Hermes] Gateway started (PID: $!)"
fi
```

## 自动监控重启（cron）

每 5 分钟检查一次，断线后自动拉起：
```bash
crontab -e
```
添加：
```
*/5 * * * * if ! pgrep -f "gateway.run" > /dev/null; then cd ~/hermes-agent && source venv/bin/activate && python3 -m gateway.run >> ~/.hermes/logs/gateway.log 2>&1 & fi
```

## 依赖安装

```bash
pip install lark-oapi
```

## 配置凭证

在 `~/.hermes/.env` 中添加：
```
FEISHU_APP_ID=<飞书AppID>
FEISHU_APP_SECRET=<飞书AppSecret>
FEISHU_CONNECTION_MODE=websocket
```

或在 `config.yaml` 的 `platforms.feishu` 中配置 `app_id` / `app_secret` / `domain` / `connection_mode`。

## 允许用户访问

```
FEISHU_ALLOWED_USERS=*   # 允许所有用户
GATEWAY_ALLOW_ALL_USERS=true
```

## 飞书应用创建步骤

1. 打开 https://open.feishu.cn/app
2. 创建企业自建应用 → 填写名称描述
3. 进入「凭证与基础信息」→ 复制 App ID 和 App Secret
4. 左侧「应用功能」→「机器人」→ 开启
5. 左侧「权限管理」→ 开通 im:message、im:message.receive_v1、im:chat
6. 「版本管理与发布」→ 创建版本 → 申请发布

## 验证连接

私聊：直接在飞书搜索机器人名称，发一条消息  
群聊：在群里 @ 机器人

## 凭证验证

```python
import urllib.request, json
data = json.dumps({"app_id": "<AppID>", "app_secret": "<AppSecret>"}).encode()
req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal",
    data=data, headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req) as r:
    resp = json.loads(r.read())
    print(resp["code"] == 0)  # True = 凭证有效
```

## Android 省电问题

**症状**：日志中出现以下错误后断线：
```
ERROR Lark: receive message loop exit, err: received 3003 (registered) ping_timeout
ERROR Lark: receive message loop exit, err: no close frame received or sent
```

**原因**：Android Doze / 省电模式限制后台网络，WebSocket 保活心跳超时被服务器踢掉。

**解决方案（按效果排序）：**

1. **Termux 加入电池白名单**（最关键）
   - 设置 → 应用 → Termux → 电池优化 → 不优化 / 无限制

2. **使用 termux-boot 开机自启**
   - 设备重启后 Termux Boot 自动执行启动脚本
   - Gateway 持续运行，不依赖前台

3. **Crontab 监控自动重启**
   - 每 5 分钟检查进程状态
   - 断线后自动拉起

## 当前环境状态

- **hermes-agent**：`/data/data/com.termux/files/home/hermes-agent/`
- **HERMES_HOME**：`/data/data/com.termux/files/home/.hermes/`
- **bashrc 路径**：`/data/data/com.termux/files/home/.bashrc`
- **termux-boot 脚本**：`~/.termux/boot/start-gateway.sh`
- **Gateway 进程**：PID 22220 (`python3 -m gateway.run`)
- **飞书 WebSocket**：`wss://msg-frontier.feishu.cn/ws/v2`
- **连接模式**：长连接（WebSocket），Hermes 主动连接飞书，无需公网 IP

## 飞书多维表格（Bitable）访问凭证

**注意（2026-04-30）**：多维表格使用的 App 凭证与 Hermes Gateway 的 App 不是同一个。

| 用途 | App ID | 凭证来源 |
|------|--------|---------|
| Hermes Gateway（消息收发） | `cli_a95a1e699d78dcb5` | `~/.hermes/.env` 的 `FEISHU_APP_ID` |
| 多维表格（Base） | **另一个 App** | 需要单独创建/配置 |

**正确读取 Bitable 的步骤**：
```python
# 1. 获取 tenant_access_token（用 Bitable 专属 App 的 app_id + app_secret）
APP_ID = "<bitable对应的App ID>"
APP_SECRET = "<bitable对应的App Secret>"

req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    data=json.dumps({'app_id': APP_ID, 'app_secret': APP_SECRET}).encode(),
    headers={'Content-Type': 'application/json'}, method='POST'
)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    token_data = json.loads(resp.read())
    if token_data.get('code') != 0:
        print(f"Auth failed: {token_data}")
        return
    tenant_token = token_data['tenant_access_token']

# 2. 用 token 访问 bitable
req2 = urllib.request.Request(
    f'https://open.feishu.cn/open-apis/bitable/v1/apps/{BASE_ID}/tables',
    headers={'Authorization': f'Bearer {tenant_token}'}
)
with urllib.request.urlopen(req2, context=ctx, timeout=10) as resp:
    print(json.loads(resp.read()))
```

**常见错误**：
- `code: 10014, msg: app secret invalid` → App Secret 不对，确认用的是 Bitable App 的 Secret，不是 Gateway 的
- `code: 99991664` → token 过期，重新获取 tenant_access_token
- `HTTP Error 400: Bad Request` → token 有效但请求格式错，通常是 URL 或 header 问题

**公共链接的 Base 直接读取**：如果用户分享的是「复制链接」形式的 Base URL（`https://xxx.feishu.cn/base/xxx`），可以尝试作为公众访问，但功能受限；完整读写权限需要正确配置 App 凭证。

> 📁 Bitable API 调用详细示例：`references/feishu-bitable-api.md`\
> 📁 流式卡片插件调试参考：`references/feishu-streaming-card-debug.md`

## 流式卡片插件（hermes-feishu-streaming-card）

**版本：** V3.2.1，安装在 `~/.hermes/plugins/hermes-feishu-streaming-card/`

### 快速诊断

```bash
# Sidecar 健康检查（端口 8765）
curl -s http://127.0.0.1:8765/health | python3 -c "
import sys,json; d=json.load(sys.stdin); m=d['metrics']
print(f'events: recv={m[\"events_received\"]} app={m[\"events_applied\"]} ign={m[\"events_ignored\"]} rej={m[\"events_rejected\"]}')
print(f'feishu: ok={m[\"feishu_send_successes\"]} fail={m[\"feishu_send_failures\"]}')
print(f'sessions: {list(d.get(\"sessions\",{}).keys())}')
"

# Sidecar 进程
ps aux | grep hermes_feishu_card | grep -v grep

# Sidecar 日志
tail -50 ~/.hermes_feishu_card/sidecar.log
```

### 已知问题与排查方向

**最常见症状：** `events_applied: 0` 且 `feishu_send_failures: N` 持续增长

可能原因（按频率排序）：
1. **aiohttp 版本不兼容（当前根因，2026-05-01）**：`feishu_client.py` 使用了 `accept_encoding='gzip, deflate'` 参数，aiohttp 3.13+ 已移除该参数，抛 `TypeError` 导致所有请求失败。修复：删除 `feishu_client.py` 中 `accept_encoding` 行，重启 sidecar 即可。
2. **权限不足**：机器人未开通 `im:message` 权限，卡片消息被拒（HTTP 500）
3. **消息 ID 冲突**：原生飞书适配器已发出普通文本消息，卡片创建时 409/500

### CardKit Markdown 能力边界（实测 2026-05-01）

**`<details>` / `<summary>` 折叠标签：❌ 不支持**，标签直接显示为纯文本，不要使用。

**以下功能实测支持**：代码块语法高亮、Markdown 表格渲染、有序/无序列表、`:emoji:` shortcode、裸 emoji。

详见：`references/feishu-card-design.md`

### 插件架构

```
gateway/run.py (hook patch)
  → hermes_feishu_card.hook_runtime.emit_from_hermes_locals()
    → POST http://127.0.0.1:8765/events
      → server._events() → _apply_event_locked()
        → CardSession.apply()
        → _send_card() → FeishuClient.send_card()
```

### 重启 Sidecar

```bash
# 查 PID
ps aux | grep hermes_feishu_card | grep -v grep

# 杀进程
kill <PID>

# 启动（terminal background=true）
python3 -m hermes_feishu_card.runner \
  --config ~/.hermes/plugins/hermes-feishu-streaming-card/config.yaml \
  --token fresh
```

### 详细调试参考

> 📁 `references/feishu-streaming-card-debug.md` — 本次调试（2026-05-01）的完整技术记录，包含 Feishu API 直接测试脚本、插件代码路径分析、日志可见性问题的临时解决方案（logging.warning 加到 gateway.log）、以及已知待排查项。
> 📁 `references/feishu-card-design.md` — 飞书卡片设计参考（2026-05-01），包含 CardKit 2.0 关键限制（note元素不支持）、markdown 支持范围、emoji 使用规范、卡片结构设计原则、Python 3.13 surrogate 编码问题与临时方案。
