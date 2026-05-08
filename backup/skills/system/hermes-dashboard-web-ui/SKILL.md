---
name: hermes-dashboard-web-ui
description: Hermes Agent Web Dashboard（web-ui）启动与修复指南
category: system
tags: [hermes, dashboard, web-ui, web, termux, frontend-build]
---

# Hermes Web Dashboard 启动与修复

## 症状
- `hermes dashboard` 启动后 http://127.0.0.1:9119 无响应
- curl 返回 `{"error":"Frontend not built. Run: cd web && npm run build"}`
- 日志显示 `Web UI build failed`
- 端口 9119 已监听但 HTTP 无响应

## 诊断步骤

### Step 1: 检查前端是否已构建
```bash
ls /data/data/com.termux/files/home/hermes-agent/hermes_cli/web_dist/
# 应该包含: index.html, assets/, fonts/, ds-assets/
# 如果为空或不存在 → 前端未构建
```

### Step 2: 检查 dashboard 进程状态
```bash
ps aux | grep dashboard | grep -v grep
curl -s -m 3 http://127.0.0.1:9119/  # HTTP 400 或无响应 = 进程异常
```

## 根因 1: 前端构建失败（最常见）

**原因**: `npm run build` 中的 `tsc` 命令不在系统 PATH 中，导致 TypeScript 编译静默失败。

**复现**:
```bash
cd ~/hermes-agent/web
npm run build
# 输出: ✗ Web UI build failed
```

**修复 - 使用正确的 PATH 构建**:
```bash
cd /data/data/com.termux/files/home/hermes-agent/web
PATH="$PWD/node_modules/.bin:$PATH" npm run build
# 验证构建成功
ls ../hermes_cli/web_dist/
```

## 根因 2: 进程跑着但 HTTP 无响应

**原因**: dashboard 进程绑定了 IPv6 或其他异常状态。

**检查**:
```bash
# 检查端口状态
python3 -c "import socket; s=socket.socket(); print(s.connect_ex(('127.0.0.1',9119)))"
# 返回 0 = 端口开，111 = 端口关
```

**修复 - 强制使用 HERMES_WEB_DIST + --insecure**:
```bash
cd /data/data/com.termux/files/home
HERMES_WEB_DIST=/data/data/com.termux/files/home/hermes-agent/hermes_cli/web_dist \
  python -m hermes_cli.main dashboard --port 9119 --no-open --insecure
```

## 完整修复命令（按顺序执行）

```bash
# 1. 构建前端（使用正确的 PATH）
cd /data/data/com.termux/files/home/hermes-agent/web
PATH="$PWD/node_modules/.bin:$PATH" npm run build

# 2. 安装 Python 依赖（如果缺失）
pip install fastapi uvicorn 2>&1 | tail -3

# 3. 启动 dashboard（必须设置 PYTHONPATH）
cd /data/data/com.termux/files/home/hermes-agent
PYTHONPATH=/data/data/com.termux/files/home/hermes-agent \
  HERMES_WEB_DIST=/data/data/com.termux/files/home/hermes-agent/hermes_cli/web_dist \
  python3 -m hermes_cli.main dashboard --port 9119 --no-open --insecure

# 4. 验证
sleep 5 && curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119/
# 应返回 200
curl -s http://127.0.0.1:9119/ | grep "<title>"
# 应返回 <title>Hermes Agent - Dashboard</title>
```

### 关键发现（2026-05-08）
- **必须设置 `PYTHONPATH`**：不使用 `python -m hermes_cli.main` 从 home 目录运行，而要从 `hermes-agent/` 目录运行并显式设置 `PYTHONPATH`
- **依赖缺失**：`hermes_cli.main` 依赖 `fastapi` 和 `uvicorn`，不在默认依赖中，需手动安装
- **pip install 要用 background**：在终端里 `pip install` 会触发后台服务器检测报错，用 `background=true` 模式
- **web_dist 已有预构建**：`/data/data/com.termux/files/home/hermes-agent/hermes_cli/web_dist/` 通常已有构建好的文件，跳过 npm build 也可能成功

## 启动后验证

```bash
# 健康检查
curl -s http://127.0.0.1:9119/api/health
# 返回 Unauthorized 是正常的（需要认证）

# 前端是否正常
curl -s http://127.0.0.1:9119/ | grep "<title>"
# 应返回 <title>Hermes Agent - Dashboard</title>
```

## lark-cli 路径（Termux 特殊）

```
/data/data/com.termux/files/home/bin/lark-cli
```
不是 `which lark-cli` 能找到的——需要用绝对路径。

初始化: `/data/data/com.termux/files/home/bin/lark-cli config init --new`

## 注意事项
- `--insecure` 在 Termux/Android 上必须使用（默认拒绝绑定非 localhost）
- `HERMES_WEB_DIST` 环境变量必须指向 `hermes_cli/web_dist` 而非 `web/dist`
- 重启 gateway 会杀掉 dashboard 进程，需要重新启动
- 如果 dashboard 在后台被杀重启，log 中可能出现 `tcsetattr: Permission denied`（无影响）
---

## Gateway 共生运行模式（重要）

Dashboard 依赖 Gateway 的进程存活状态：Gateway 在跑 Dashboard 才跑，Gateway 停了 Dashboard 也停。

**不要**用独立的 cron 定时拉起 Dashboard——这会导致 Gateway 停了而 Dashboard 独自跑着，浪费资源且不符合预期。

正确做法：用 watchdog 脚本，每分钟检查 Gateway 是否存活，据此决定启动/停止 Dashboard。

**启动脚本** `~/.hermes/scripts/watchdog-dashboard.sh`（已注册 Cron `* * * * *`）：
```bash
#!/bin/bash
# Dashboard watchdog — 保持 Web Dashboard 与 Gateway 同在
# Gateway 跑着的时候，dashboard 就必须在；gateway 没跑，dashboard 也休息

GATEWAY_PID=$(pgrep -f "python3 -m gateway.run" 2>/dev/null | head -1)
DASHBOARD_PID=$(pgrep -f "hermes_cli.main dashboard" 2>/dev/null | head -1)
DASHBOARD_PORT=9119

if [ -n "$GATEWAY_PID" ]; then
    # Gateway 在跑
    if [ -z "$DASHBOARD_PID" ]; then
        # Dashboard 没跑 → 启动它
        cd /data/data/com.termux/files/home/hermes-agent
        PYTHONPATH=/data/data/com.termux/files/home/hermes-agent \
        HERMES_WEB_DIST=/data/data/com.termux/files/home/hermes-agent/hermes_cli/web_dist \
        nohup python3 -m hermes_cli.main dashboard --port $DASHBOARD_PORT --no-open --insecure > /dev/null 2>&1 &
    else
        # 都在跑 → 检查端口
        if ! curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$DASHBOARD_PORT/ | grep -q "200"; then
            # 端口不通 → 重启 dashboard
            kill $DASHBOARD_PID 2>/dev/null
            sleep 1
            cd /data/data/com.termux/files/home/hermes-agent
            PYTHONPATH=/data/data/com.termux/files/home/hermes-agent \
            HERMES_WEB_DIST=/data/data/com.termux/files/home/hermes-agent/hermes_cli/web_dist \
            nohup python3 -m hermes_cli.main dashboard --port $DASHBOARD_PORT --no-open --insecure > /dev/null 2>&1 &
        fi
    fi
else
    # Gateway 没跑 → dashboard 也关掉
    if [ -n "$DASHBOARD_PID" ]; then
        kill $DASHBOARD_PID 2>/dev/null
    fi
fi
```

**注册 Cron**：
```
* * * * * bash /data/data/com.termux/files/home/.hermes/scripts/watchdog-dashboard.sh
```

**关键判断逻辑**：
- Gateway PID 存在 + Dashboard PID 不存在 → 启动 Dashboard
- Gateway PID 存在 + Dashboard PID 存在 + 端口 9119 不通 → 重启 Dashboard
- Gateway PID 不存在 → 杀掉 Dashboard

---

## 附：Dashboard 维护补充（来源：`hermes-dashboard-maintenance`）

### 启动命令

```bash
cd /data/data/com.termux/files/home/hermes-agent/web
PATH="$PWD/node_modules/.bin:$PATH" npm run build
HERMES_WEB_DIST=/data/data/com.termux/files/home/hermes-agent/hermes_cli/web_dist hermes dashboard --port 9119 --no-open --insecure
```

### Streaming Card Sidecar 启动（飞书流式卡片）

```bash
python3 -m hermes_feishu_card.runner --config /data/data/com.termux/files/home/.hermes/plugins/hermes-feishu-streaming-card/config.yaml
```

健康检查：
```bash
curl -s http://127.0.0.1:8765/health
# {"status": "healthy", "active_sessions": 0, ...}
```

### 常见问题

| 症状 | 原因 | 解决 |
|------|------|------|
| `tsc: not found` | `tsc` 不在 PATH | `PATH="$PWD/node_modules/.bin:$PATH" npm run build` |
| 返回 `"Frontend not built"` | `HERMES_WEB_DIST` 未设置 | 设置为 `hermes_cli/web_dist` |
| 端口 9119 被占用 | 进程残留 | `ss -tlnp \| grep 9119` 然后 `kill <PID>` |
| Dashboard 重启后不自动启动 | gateway 重启会杀进程 | 需要 cron 保持存活 |
| `ModuleNotFoundError: No module named 'hermes_cli'` | 从错误目录运行或未设置 PYTHONPATH | 必须从 `hermes-agent/` 目录运行并设置 `PYTHONPATH=/data/data/com.termux/files/home/hermes-agent` |
| `ModuleNotFoundError: No module named 'fastapi'` | Web UI 依赖未安装 | `pip install fastapi uvicorn` |
| `pip install` 报错 "Foreground command uses '&'" | pip 检测到后台进程模式误判 | 用 `background=true` 模式运行 pip install |
| TypeScript 构建大量组件 API 报错 | `@nous-research/ui` 版本与代码不匹配 | 跳过构建，`web_dist/` 通常已有预构建文件 |
