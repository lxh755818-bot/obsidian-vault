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
