# Source: `hermes-dashboard-maintenance`

---
name: hermes-dashboard-maintenance
description: Hermes Agent Web UI (Dashboard) 启动与故障排查
category: system
tags: [hermes, dashboard, web-ui, termux]
required_environment_variables: []
required_commands: [node, npm]
---

# Hermes Dashboard 维护手册

## 启动命令

```bash
cd /data/data/com.termux/files/home/hermes-agent/web
PATH="$PWD/node_modules/.bin:$PATH" npm run build
HERMES_WEB_DIST=/data/data/com.termux/files/home/hermes-agent/hermes_cli/web_dist hermes dashboard --port 9119 --no-open --insecure
```

## 常见问题

### 1. `tsc: not found`

**症状**：`npm run build` 报错 `sh: tsc: not found`

**原因**：`tsc` 不在 PATH 环境变量中

**解决**：使用绝对路径
```bash
PATH="$PWD/node_modules/.bin:$PATH" npm run build
```

### 2. Web UI 启动后返回 "Frontend not built"

**症状**：Dashboard 进程在跑，端口 9119 开放，但 HTTP 返回 `{"error":"Frontend not built..."}`

**原因**：`HERMES_WEB_DIST` 环境变量未设置或指向空目录

**解决**：设置正确的构建产物目录
```bash
HERMES_WEB_DIST=/data/data/com.termux/files/home/hermes-agent/hermes_cli/web_dist
```

### 3. 端口 9119 被占用但进程不在

**症状**：`Address already in use`

**解决**：
```bash
# 检查端口占用
ss -tlnp | grep 9119
# kill 占用进程
kill <PID>
```

### 4. `--insecure` 与 `0.0.0.0`

- Dashboard 默认绑定 `127.0.0.1`，不需要 `--insecure`
- 绑定 `0.0.0.0`（允许外部访问）需要 `--insecure`（因为暴露 API keys）
- 在 Termux/Android 上通常只需要 `127.0.0.1`

### 5. 重启后 Dashboard 被杀掉

Dashboard 需要手动重启，或用 cron 保持存活。Gateway 重启也会把 Dashboard 进程杀掉。

## 验证 Dashboard 是否正常

```bash
curl -s http://127.0.0.1:9119/ | head -5
# 正常返回 HTML
```

## Streaming Card Sidecar 启动（飞书流式卡片）

```bash
python3 -m hermes_feishu_card.runner --config /data/data/com.termux/files/home/.hermes/plugins/hermes-feishu-streaming-card/config.yaml
```

健康检查：
```bash
curl -s http://127.0.0.1:8765/health
# {"status": "healthy", "active_sessions": 0, ...}
```

## 构建产物位置

- 构建输出：`/data/data/com.termux/files/home/hermes-agent/hermes_cli/web_dist/`
- 包含：`index.html`, `assets/`, `fonts/`, `ds-assets/`
