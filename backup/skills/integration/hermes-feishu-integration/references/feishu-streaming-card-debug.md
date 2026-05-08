# Feishu 流式卡片插件调试参考

> 本次调试记录：2026-05-01，插件版本 V3.2.1

## 已知状态

- Sidecar 运行端口：`8765`
- Config 路径：`~/.hermes/plugins/hermes-feishu-streaming-card/config.yaml`
- Hook 装入位置：`gateway/run.py` 第 5249 行
- Sidecar 进程检查：`ps aux | grep hermes_feishu_card | grep -v grep`
- Sidecar 健康状态：`curl http://127.0.0.1:8765/health`

## 快速诊断命令

```bash
# 1. Sidecar 健康状态（关键指标）
curl -s http://127.0.0.1:8765/health | python3 -c "
import sys,json; d=json.load(sys.stdin)
m=d['metrics']
print(f'events: recv={m[\"events_received\"]} app={m[\"events_applied\"]} ign={m[\"events_ignored\"]} rej={m[\"events_rejected\"]}')
print(f'feishu: ok={m[\"feishu_send_successes\"]} fail={m[\"feishu_send_failures\"]}')
print(f'sessions: {list(d.get(\"sessions\",{}).keys())}')
print(f'last_update_error: {d[\"diagnostics\"][\"last_update_error\"]}')
"

# 2. Sidecar 日志
tail -50 ~/.hermes_feishu_card/sidecar.log

# 3. Gateway 日志中的卡片相关错误
tail -100 ~/.hermes/logs/gateway.log | grep -E "feishu|card|HERMES_FEISHU" | tail -20
```

## 常见症状与根因

### 症状：events_applied=0，所有事件被 ignored

**现象：**
```
events_received: 120 | events_applied: 0 | events_ignored: 118 | events_rejected: 2
feishu_send_successes: 0 | feishu_send_failures: 2
```

**根因（已确认，2026-05-01）：**
`feishu_client.py` 的 `_request_json()` 方法中使用了 `accept_encoding='gzip, deflate'` 参数：

```python
async with session.request(
    ...,
    accept_encoding='gzip, deflate',  # ← aiohttp 3.13+ 不支持此参数
) as response:
```

aiohttp 3.13.5（Termux 现有版本）已移除 `accept_encoding` 参数，任何使用该参数的请求都会抛 `TypeError` 崩溃，导致所有 Feishu API 调用直接失败（HTTP 502）。

**验证方法：**
```python
import aiohttp, asyncio
async def test():
    async with aiohttp.ClientSession() as s:
        # 这行会抛 TypeError
        async with s.request('POST', 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
                             json={'app_id':'...','app_secret':'...'}, accept_encoding='gzip, deflate') as r:
            pass
asyncio.run(test())
# → TypeError: ClientSession._request() got an unexpected keyword argument 'accept_encoding'
```

**修复（已应用）：**
删除 `feishu_client.py` 中的 `accept_encoding='gzip, deflate'` 行即可。aiohttp 3.13+ 默认压缩，无需显式声明。

```python
# 修复前（feishu_client.py ~line 144）
async with session.request(method, url, params=params, json=json_body, headers=headers,
    accept_encoding='gzip, deflate',  # 删除此行
) as response:

# 修复后
async with session.request(method, url, params=params, json=json_body, headers=headers,
) as response:
```

**修复后验证：**
```bash
curl -s http://127.0.0.1:8765/health | python3 -c "
import sys,json; d=json.load(sys.stdin); m=d['metrics']
print(f'app={m[\"events_applied\"]} ok={m[\"feishu_send_successes\"]} sessions={list(d[\"sessions\"].keys())}')"
# 期望：app=1 ok=1 sessions=['test_msg_xyz']
```

**排查方向（补充）：**
1. **优先确认 aiohttp 版本**：`python3 -c "import aiohttp; print(aiohttp.__version__)"` — 如果 ≥3.9，可能存在参数兼容问题
2. Feishu API 是否可达：`curl -s https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal`
3. 机器人 `im:message` 权限是否开通（卡片消息需要 `msg_type: interactive`）

### 症状：curl http://127.0.0.1:8765/health 返回空 / 连接被拒绝

**根因：** Sidecar 进程挂了或根本没启动

**排查：**
```bash
ps aux | grep hermes_feishu_card | grep -v grep
ss -tlnp | grep 8765
```

### 症状：日志完全看不到（print 语句不输出）

**根因：** 插件 runner 使用 `web.run_app(..., print=None)` 禁用了 stdout/stderr，print() / sys.stderr.write() 都不输出

**临时调试方法：** 在 `/events` handler 入口加 `logger.warning()`（logging 模块），然后查看 `gateway.log` 或单独运行 sidecar 的终端输出

## Feishu API 直接测试

```python
import json, urllib.request

# 获取 token
req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({"app_id": "cli_a95a1e699d78dcb5", "app_secret": "hnvbzkROjEbjJjYDJA1gdjSzx2DEMOgT"}).encode(),
    headers={"Content-Type": "application/json"}, method="POST"
)
with urllib.request.urlopen(req, timeout=10) as r:
    token = json.loads(r.read())["tenant_access_token"]

# 发送测试卡片
card = {
    "schema": "2.0",
    "config": {"update_multi": True, "summary": {"content": "思考中"}},
    "header": {"template": "indigo", "title": {"tag": "plain_text", "content": "Hermes Agent"}, "subtitle": {"tag": "plain_text", "content": "思考中"}},
    "body": {"elements": [{"tag": "markdown", "element_id": "main_content", "content": "Test"}]}
}

req2 = urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=json.dumps({"receive_id": "oc_2e5cc02fdda5aef65a7f9ca03127eda5", "msg_type": "interactive", "content": json.dumps(card)}).encode(),
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"}, method="POST"
)
with urllib.request.urlopen(req2, timeout=10) as r:
    result = json.loads(r.read())
    print(result.get("code"), result.get("msg"))  # 0 success = 正常
```

## 插件架构关键文件

| 文件 | 作用 |
|------|------|
| `hook_runtime.py` | 从 Hermes Gateway 注入，发送事件到 sidecar |
| `server.py` | aiohttp Web 服务，处理 /events，端到端逻辑 |
| `session.py` | CardSession 类，管理卡片状态和 apply() 逻辑 |
| `render.py` | 卡片渲染，构建 Feishu CardKit JSON |
| `feishu_client.py` | Feishu API 调用（tenant token + 发送卡片） |
| `runner.py` | 入口，`web.run_app(print=None)` 禁用了日志输出 |

## 关键代码路径（message.started 事件）

```
Hermes Gateway (run.py)
  → hook_runtime.emit_from_hermes_locals(locals())
    → POST http://127.0.0.1:8765/events
      → server._events()
        → SidecarEvent.from_dict(payload)
        → _apply_event_locked(request, event)
          → if event.event == "message.started":
              → session = CardSession(...)
              → session.apply(event)
              → _send_card(chat_id, card)  ← 可能在这里失败
                → FeishuClient.send_card(chat_id, card)
                  → POST /im/v1/messages → Feishu 返回
```

## 重启 Sidecar 命令

```bash
# 杀进程（先查 PID）
kill $(ps aux | grep hermes_feishu_card | grep -v grep | awk '{print $2}')

# 启动（后台运行，用 terminal background=true）
python3 -m hermes_feishu_card.runner \
  --config ~/.hermes/plugins/hermes-feishu-streaming-card/config.yaml \
  --token <任意标识字符串>

# 验证
sleep 3 && curl -s http://127.0.0.1:8765/health
```

## 已知问题（2026-05-01）

### ✅ 已解决：accept_encoding 参数不兼容

**问题**：`feishu_client.py` 使用 `accept_encoding='gzip, deflate'`，aiohttp 3.13+ 不支持，抛 `TypeError` 导致所有请求失败。

**修复**：删除该行，已在 `~/.hermes/plugins/hermes-feishu-streaming-card/hermes_feishu_card/feishu_client.py` 中应用。

**验证**：`events_applied: 1`, `feishu_send_successes: 1` ✅

### 🔶 待排查：日志不可见

**问题**：runner 的 `print=None` 导致所有调试输出丢失，临时加 `print()` / `sys.stderr.write()` 均无效。

**临时方案**：在 server.py 中使用 `logger.warning()`（logging 模块），输出会进入 gateway.log。

## 待排查项

- [x] ~~在 Termux 环境下测试 aiohttp `ClientSession` 是否能正常请求 `https://open.feishu.cn`~~ ✅ 确认正常
- [x] ~~确认 Feishu 机器人的 `im:message` 权限已开通~~ ✅ 权限正常
- [x] ~~尝试用 `accept_encoding` 参数绕过 Feishu API 的压缩响应问题~~ ✅ 已解决，删除了该参数
- [ ] 验证实际对话时流式卡片是否正常更新（当前只测试了 message.started 单次事件）
- [ ] 测试 `message.completed` 事件是否正确关闭 session 并更新卡片为"已完成"
