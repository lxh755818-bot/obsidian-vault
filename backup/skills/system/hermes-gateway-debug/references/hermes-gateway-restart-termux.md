# Source: `hermes-gateway-restart-termux`

---
name: hermes-gateway-restart-termux
description: Hermes Gateway 在 Termux 上的重启方法 — 解决 PID 文件残留导致进程无法启动的问题。
version: 1.0.0
author: 小哈
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [gateway, termux, restart, pid-file, feishu]
    platform: termux
---

# Hermes Gateway Termux 重启指南

## 核心问题

在 Termux 上，gateway 进程被 SIGTERM 关闭后（比如系统休眠、进程崩溃），PID 文件 `~/.hermes/gateway.pid` 可能残留，但实际进程已不存在。这会导致后续所有 `hermes gateway start/restart` 命令失败：

```
ERROR __main__: PID file race lost to another gateway instance. Exiting.
```

`gateway_state.json` 显示 `"gateway_state": "draining"` 也说明 gateway 未在运行。

## 诊断步骤

### 1. 检查 gateway 是否真的在运行
```bash
ps aux | grep -E "hermes.*gateway" | grep -v "grep\|snap\|bash"
```
无输出 = gateway 未运行。

### 2. 检查 gateway_state.json
```bash
cat ~/.hermes/gateway_state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('state:', d.get('gateway_state'), 'updated:', d.get('updated_at'))"
```
- `draining` = 正在关闭，未运行
- `running` = 正常运行

### 3. 检查 PID 文件是否残留
```bash
cat ~/.hermes/gateway.pid
# 对比实际进程
ps aux | grep $(cat ~/.hermes/gateway.pid) | grep -v grep
```
无输出 = PID 文件残留，进程已不存在。

## 正确重启步骤

```bash
# 1. 清理残留 PID 文件（关键！）
rm -f ~/.hermes/gateway.pid

# 2. 使用 run --replace 启动（不是 start！）
hermes gateway run --replace 2>&1 &

# 3. 等待启动
sleep 15

# 4. 验证
ps aux | grep -E "hermes.*gateway" | grep -v "grep\|snap\|bash"
cat ~/.hermes/gateway_state.json
```

## 为什么不能用 `hermes gateway restart`？

Termux 没有系统服务管理器，`hermes gateway start` 本身就是启动一个前台进程，不支持后台服务。所以要用 `hermes gateway run --replace`，配合 `&` 让它后台运行。

## PID 文件机制（关键知识）

`get_running_pid()` 验证逻辑（`gateway/status.py`）:
1. `os.kill(pid, 0)` 检查进程是否存在
2. 比较 `start_time` 与进程实际启动时间是否一致（防 PID 复用）
3. `_looks_like_gateway_process(pid)` 检查 `/proc/<pid>/cmdline` 是否含 `gateway/run.py`
4. `_record_looks_like_gateway(record)` 检查 PID 文件中的 `kind` 字段

**重要**: 绝对不要手动把 hermes CLI 的 PID 写入 `gateway.pid`。Gateway PID 文件由 `write_pid_file()` 在 gateway 子进程启动时自动创建（O_CREAT|O_EXCL 原子操作）。残留时**只删除文件**，不要手动编辑。

## 验证飞书连接

```bash
cat ~/.hermes/gateway_state.json | python3 -c "import sys,json; d=json.load(sys.stdin); fs=d['platforms']['feishu']; print('feishu:', fs['state'], 'error:', fs.get('error_message','none'))"
```

连接正常会显示 `connected`。

## Web UI Dashboard

启动命令：
```bash
hermes dashboard --port 9119 --host 127.0.0.1
```

**重启后不自动拉起**：设备重启（Termux boot）后，hermes 主进程可能自动恢复，但 `dashboard` 不会随系统自启，需手动执行上述命令。

启动后约需 **30 秒** 构建 Web UI（首次运行），期间 curl 会报连接拒绝，稍后再试即可。

**Android/Termux 限制**：
- `--host 0.0.0.0` 被安全策略拒绝，必须用 `127.0.0.1`
- `uvicorn[standard]` 在 Android 上失败 — `watchfiles` 需要 Rust 编译（maturin）
  ```bash
  # 安装正确的依赖（不含 [standard]）
  pip install fastapi uvicorn
  ```
- 电脑访问需先运行: `adb forward tcp:9119 tcp:9119`，然后浏览器访问 `http://127.0.0.1:9119`

## 症状对照表

| 症状 | 原因 | 解决 |
|---|---|---|
| `PID file race lost` | PID 文件残留，进程已死 | `rm ~/.hermes/gateway.pid` |
| `draining` 状态不变 | gateway 未启动 | `hermes gateway run --replace` |
| 飞书消息无响应但日志有记录 | gateway 进程挂了 | 重启 gateway |
| `hermes gateway start` 报错不支持 | Termux 无 service manager | 用 `run --replace` |
| `ModuleNotFoundError: No module named 'httpx'` | 用系统 python 而非 venv python | 必须用 `~/hermes-agent/venv/bin/python -m gateway.run` |

## PITFALL: 必须用 venv python，不能用系统 python

Gateway 依赖 httpx、lark-oapi 等包，它们装在 hermes-agent 的 venv 里，不在系统 python 路径下。

**错误：**
```bash
python3 -m gateway.run
# → ModuleNotFoundError: No module named 'httpx'
```

**正确：**
```bash
/data/data/com.termux/files/home/hermes-agent/venv/bin/python -m gateway.run
```

或如果 cd 到项目目录：
```bash
cd ~/hermes-agent && ./venv/bin/python -m gateway.run
```

**如何确认 venv 路径：**
```bash
ls ~/hermes-agent/venv/bin/python*
```
