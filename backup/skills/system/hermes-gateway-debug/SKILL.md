---
name: hermes-gateway-debug
description: Hermes Gateway 异常断连诊断 — 从症状到根因的系统化排查流程
category: system
tags: [hermes, gateway, debug, feishu, websocket, termux]
---

# Hermes Gateway 异常断连诊断

## 症状
- 飞书消息突然无响应
- 网关进程看起来在跑，但不再接收消息
- `errors.log` / `gateway.log` 中出现 `Unclosed client session`

## Step 0: 快速状态确认（回答"网关状态确认"类查询）

如果只需要回答"网关是否正常运行"，不需要完整诊断流程：

```bash
# 进程存活检查
ps aux | grep -E "hermes.*gateway|python3 -m gateway.run" | grep -v grep

# API Server 健康检查（端口见 config.yaml api_server.port）
curl -s --max-time 3 -H "Authorization: Bearer <API_KEY>" http://127.0.0.1:8642/health

# 飞书 WebSocket 连接状态（查日志最新 entry）
tail -1 ~/.hermes/logs/gateway.log | grep -E "connected|disconnected"
```

健康判断标准：
- 进程存在 + API `/health` 返回 `{"status":"ok"}` → API Server 正常
- 日志最新行含 `connected to wss://msg-frontier.feishu.cn` → 飞书 WS 已连接
- 两者都有 = 网关完全正常，无需进一步诊断

## 诊断步骤

### Step 1: 进程 + 日志快速检查
```bash
# 进程是否存活
ps aux | grep -E "hermes|gateway|lark" | grep -v grep

# 找最新日志文件
find ~/.hermes/logs -name "*.log" -newer /tmp -exec ls -la {} \; 2>/dev/null | head -20
```

### Step 2: 核心日志分析（按顺序）
```bash
# 错误日志 — 找 Unclosed client session
tail -200 ~/.hermes/logs/errors.log

# 网关运行日志 — 找 disconnect/reconnect/ping timeout
tail -200 ~/.hermes/logs/gateway.log

# MCP stderr（飞书重连时会重启 MCP server）
tail -50 ~/.hermes/logs/mcp-stderr.log
```

### Step 3: 定位根因模式

**模式 A：`Unclosed client session` + 同一 session 地址反复出现**
- 根因：上游 `lark-oapi` WSClient 重连时未正确关闭旧 aiohttp session
- 确认：`grep "0x793\|0x792" ~/.hermes/logs/gateway.log` 看是否是固定地址
- 相关 hermes-agent issue: #10616（尚未修复）
- 影响版本：所有当前版本（v0.11.0 + lark-oapi 1.5.5）

**模式 B：`ping failed` / `keepalive ping timeout`**
- 根因：飞书 WebSocket 底层连接超时
- 表现：lark_oapi SDK 消息循环退出，但进程未退出（zombie）
- 相关 issue: #10616

**模式 C：MCP server 反复重启**
- `mcp-stderr.log` 中每秒一次 `starting MCP server` 循环
- 根因：飞书重连触发 MCP server 重启，但不影响主要功能

### Step 4: 版本检查
```bash
# hermes-agent 版本
cd ~/hermes-agent && git log --oneline -3 && git remote -v

# lark-oapi 版本
pip show lark-oapi | grep Version

# 检查 upstream 是否有新修复
cd ~/hermes-agent && git fetch origin && git log --oneline HEAD..origin/main | head -10
```

### Step 5: 检查 upstream issue
```bash
# 搜索 hermes-agent 是否有相关 fix
cd ~/hermes-agent && git log --oneline HEAD..origin/main --grep="feishu\|zombie\|ping timeout\|ws.*reconnect" 2>/dev/null
```

## 当前已知未修复问题

| Issue | 问题 | 状态 |
|-------|------|------|
| #10616 | Feishu WS 断连导致 zombie 进程 | 尚未修复 |
| lark-oapi upstream | WSClient 重连时 aiohttp session 泄漏 | 尚未修复 |

## 恢复操作

当前网关通过进程重启自动恢复：
- 旧的带泄漏进程退出
- 新进程启动并重新连接飞书 WS
- 无需手动干预

如需手动重启（Termux）：
```bash
# 方法1: 使用 skill
skill_view hermes-gateway-restart-termux

# 方法2: 手动
pkill -f "gateway.run" && cd ~/hermes-agent && hermes gateway
```

## 预防性监控

建议配置外部监控检测 `Unclosed client session` 爆发：
- 监控 `errors.log` 中 `Unclosed client session` 计数
- 连续出现 > 50 次/分钟 → 触发告警
- 当前无奈解：等待自动重连（每次都会重新创建进程）
