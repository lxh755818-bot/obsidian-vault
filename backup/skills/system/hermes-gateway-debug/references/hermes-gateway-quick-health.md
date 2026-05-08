# Hermes Gateway 快速健康检查卡

## 一句话命令

```bash
# 进程 + API Server + 飞书WS 一条命令搞定
ps aux | grep -E "gateway.run" | grep -v grep && curl -s --max-time 2 http://127.0.0.1:8642/health && tail -1 ~/.hermes/logs/gateway.log | grep -q "connected" && echo "Feishu WS: OK"
```

## 各组件检查

| 组件 | 检查命令 | 正常标志 |
|------|----------|----------|
| Gateway 进程 | `ps aux \| grep gateway.run \| grep -v grep` | 有输出 |
| API Server | `curl -s --max-time 3 http://127.0.0.1:8642/health` | `{"status":"ok",...}` |
| 飞书 WS | `tail -1 ~/.hermes/logs/gateway.log` | 含 `connected to wss://msg-frontier.feishu.cn` |
| mem9 同步 | `tail ~/.hermes/logs/gateway.log \| grep mem9` | 无 `sync failed` |

## API Server 认证

API Server 需要 Bearer token，放在 HTTP Header：
```
Authorization: Bearer <API_KEY>
```

API Key 位置：`~/.hermes/config.yaml` → `platforms.api_server.key`

> 注意：即使 config.yaml 中配置了 key，gateway 启动时仍可能报警 "No API key configured"（读取的是环境变量 `API_SERVER_KEY`），但实际请求仍需带 token 才能访问。

## 常见日志关键字

```
# 正常
connected to wss://msg-frontier.feishu.cn   ← 飞书 WS 已连接
API server listening on http://127.0.0.1:8642  ← API Server 已启动
Flushing text batch                           ← 消息处理中

# 警告（通常无害）
mem9 sync failed: timed out          ← mem9 网络抖动，不影响 gateway
mcp-stderr: starting MCP server      ← MCP 重启，不影响主功能
No API key configured                ← 仅环境变量警告，可忽略

# 故障
Unclosed client session              ← WS session 泄漏，见 #10616
ping failed / keepalive ping timeout ← 飞书 WS 断连
draining                             ← gateway 正在关闭
```

## 端口速查

| 服务 | 端口 | 用途 |
|------|------|------|
| API Server | `8642`（默认） | Local HTTP API，Hermes 所有平台消息入口 |
| Web UI | `9119`（默认） | Dashboard 可视化界面 |

端口从 `~/.hermes/config.yaml` 的 `api_server.port` 和 `dashboard.port` 读取。
