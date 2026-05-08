# EvoMap 任务排查路径（Session 沉淀）

## 快速查询节点状态

```bash
# 查声望、积分、等级
curl -s -X POST "https://evomap.ai/a2a/hello" \
  -H "Authorization: Bearer $EVOMAP_NODE_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"protocol":"gep-a2a","protocol_version":"1.0.0","message_type":"hello","message_id":"msg_xxx","sender_id":"node_401b20c3dc6f18ea","timestamp":"..."}'

# 查我的任务列表
curl -s "https://evomap.ai/a2a/task/my?node_id=node_401b20c3dc6f18ea" \
  -H "Authorization: Bearer $EVOMAP_NODE_SECRET"
```

## 任务提交状态完整排查

### Step 1：查任务列表
```
GET https://evomap.ai/a2a/task/my?node_id={node_id}
```
返回字段：`task_id`, `status`, `my_submission_id`, `my_submission_status`, `my_submission_asset`

### Step 2：查具体提交记录
```
GET https://evomap.ai/a2a/task/{task_id}/submissions?sender_id={node_id}
```
关键字段：
- `asset_id`：空="" = 被拒的首要特征
- `status`：pending / rejected / accepted

### Step 3：对比 asset_id
| asset_id | 含义 |
|----------|------|
| 空 "" | publish步骤被跳过，或publish失败 |
| sha256:... | 已通过publish获得真实asset_id |

## 任务1被拒完整复盘（cm1049939700cc0617415b0db）

| 时间 | 事件 |
|------|------|
| 2026-04-29 12:00 | submit调用，asset_id=""，状态rejected |
| 2026-04-29 13:26 | 另一个节点（node_1）提交被接受，任务标记completed |
| 根因 | 跳过了publish步骤，直接submit |

**教训**：任何任务都必须走 publish→submit 完整流程，不能跳步。

## ⚠️ Canonicalize Bug（2026-05-01 实测）

**问题**：publish 时一直报 `gene_asset_id_verification_failed`

**根因**：canonicalize 函数里过滤了 `null` 和 `[]`：
```python
# ❌ 错误：过滤 null/[] 导致 hash 不匹配
{k: v for k, v in sorted(obj.items()) if v is not None and v != []}

# ✅ 正确：Hub 明确要求保留 null/[]（"null/undefined become 'null'"）
{k: v for k, v in sorted(obj.items())}
```

**症状对比**：
- 用过滤版 canonicalize → Hub 算出的 hash ≠ 我算出的 → 422
- 用不过滤版 canonicalize → 完全匹配 → 200 accept

**验证**：Hub 的 error message 里 example 写的是 `null/undefined become 'null'`，说明 null 要参与 hash。

**涉及的任务**：任务4（cm8152fc...，NeRF/GS 集成）

## 任务3过期未处理（cmo9nt8jj0w7v882meb3kk5xq）

- 认领时间：2026-04-22 06:16
- 过期时间：2026-04-29 06:16
- 提交asset_id：sha256:de858482a513c60b...（有真实asset_id，流程正确）
- 状态：pending（但任务已过期）
- 结论：过期任务即使提交pending也不会被审核

## ⚠️ Python子进程环境变量问题（2026-05-01 实测）

**症状**：`source ~/.hermes/.env && python3 -c "..."` 里 Python 读到环境变量是**空的**或**旧值**，导致 401。

**根因**：`source` 是 shell 内建命令，`&&` 只保证 shell 执行完，但 `python3 -c` 启动的是**新子进程**，不继承父shell的 export 变量。

**错误模式**：
```bash
# ❌ 错误：python子进程读不到 EVOMAP_NODE_SECRET
source ~/.hermes/.env 2>/dev/null
python3 -c "import os; print(os.environ.get('EVOMAP_NODE_SECRET'))"  # 输出 None
```

**正确模式**：在 Python 内部读取 .env 文件，不依赖 shell 穿透：
```python
import os
with open(os.path.expanduser('~/.hermes/.env')) as f:
    for line in f:
        if '=' in line:
            k, v = line.strip().split('=', 1)
            os.environ[k] = v
node_secret = os.environ.get('EVOMAP_NODE_SECRET', '')
```

**教训**：所有涉及 secret 的 Python 脚本一律在脚本内部读取 `.env`，不要依赖 shell 环境变量穿透。

## 401诊断标准化流程（2026-05-01）

遇到 401，分三步走：

### Step 1：Hello测试（不修改状态）
```python
import urllib.request, json, ssl, os
with open(os.path.expanduser('~/.hermes/.env')) as f:
    for line in f:
        if '=' in line:
            k, v = line.strip().split('=', 1)
            os.environ[k] = v
node_secret = os.environ.get('EVOMAP_NODE_SECRET', '')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(
    'https://evomap.ai/a2a/hello',
    data=json.dumps({"protocol": "gep-a2a", "protocol_version": "1.0.0", "message_type": "hello", "message_id": "msg_test", "sender_id": "node_401b20c3dc6f18ea", "timestamp": "2026-05-01T00:00:00Z", "payload": {}}).encode(),
    headers={'Authorization': 'Bearer {}'.format(node_secret), 'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
    result = json.loads(resp.read())
print(result.get('payload', {}).get('node_secret_status'))  # 应输出 active
```

### Step 2：如果 hello 正常但 API 401 → rotate secret
```python
# rotate
req = urllib.request.Request(
    'https://evomap.ai/a2a/hello',
    data=json.dumps({"protocol": "gep-a2a", "message_type": "hello", "sender_id": "node_401b20c3dc6f18ea", "timestamp": "...", "payload": {"rotate_secret": True}}).encode(),
    headers={'Authorization': 'Bearer {}'.format(old_secret), 'Content-Type': 'application/json'}
)
# 拿 new_secret → 更新 ~/.hermes/.env
```

### Step 3：验证新secret可用后再继续

**本session教训**：在确认hello正常之前，不要连续重试同一个 secret（会被标记）。先rotate，验证新secret，再做业务操作。

## 隐私保护规范（2026-05-01 确认）

**对外发送消息前，必须过滤以下内容**：

| 类型 | 示例 | 处理方式 |
|------|------|----------|
| 手机号 | 18307655818 | 替换为 `***` 或省略 |
| API Key / Node Secret | `e75ea6912aa8...` | 只显示前后4字符 `e75e...68ba` |
| 第三方Key | 各类token | 同上 |
| 邮箱 | lxh755818@outlook.com | 省略或显示域名 |

**原则**：用户要求完整落地 + 安全意识高，对外沟通默认检查，敏感内容替换为 `***`。不篡改事实，但也不暴露隐私。
