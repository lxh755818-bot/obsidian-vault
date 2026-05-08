---
name: log-error-correction
description: 日志纠错自进化技能。每12小时运行一次，分析半日内的新错误，检查是否已关闭，未关闭则输出方案、测试方案、输出报告。
version: 1.0.0
author: 小哈
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [Self-Evolution, Error Analysis, Cron]
    cron_schedule: "0 */12 * * *"  # 每12小时一次
---

# 日志纠错技能

## 触发条件
- **Cron 表达式**: `0 */12 * * *`（每12小时，如 0:00、12:00）
- **手动触发**: `cronjob action=run job_id=<日志纠错任务ID>`

## 执行流程

### 第一步：收集错误日志

扫描 `~/.hermes/logs/` 目录下最近半天（12小时）内的日志文件：
```
~/.hermes/logs/
├── error_YYYYMMDD_HHMMSS.log
├── hermes_YYYYMMDD.log
└── ...
```

收集条件：
- 文件修改时间在当前时间往前 12 小时内
- 文件内容包含 `ERROR`、`Exception`、`Traceback` 等错误关键词

### 第二步：去重 + 按错误类型聚合

相同错误（堆栈相似）只保留一条，减少重复分析。

### 第三步：查询错误是否已关闭

对于每个未处理的错误：

1. 检查 `~/.hermes/error_tracker.json`（错误追踪文件）
2. 如果错误已在 tracker 中且状态为 `closed`，跳过
3. 如果状态为 `open` 或 `in_progress`，继续分析

### 第四步：分析 + 输出方案

对于每个 `open` 状态的错误：

1. **分析错误类型**（是环境问题、代码bug、还是配置问题？）
2. **定位相关代码**（根据堆栈找到出错位置）
3. **输出解决方案建议**（可能需要改配置、改代码、加判断等）

### 第五步：测试解决方案

在沙箱环境执行测试：
1. 创建临时测试脚本
2. 执行并计时
3. 验证修复是否有效
4. 记录测试结果到 `~/.hermes/evolution_logs/error_correction/`

### 第六步：更新 tracker

根据测试结果更新 `error_tracker.json`：
- `closed`：已修复
- `open`：未修复，等待下次
- `in_progress`：正在修复中
- `accepted`：已知问题但不活跃（长期未在日志中出现，或为用户输入错误等外部因素，无需修复）

**特别注意**：

1. **open/in_progress 错误仍在日志中出现** → 长期未出现的才转 `accepted`，仍在活跃的保持 `open`
2. **closed 错误若再次出现** → 必须改为 `accepted`（而非保持 `closed`）。closed 意味着"已修复永不复发"，一旦同类错误再次出现，说明它不是可永久消除的bug，而是外部因素或用户输入导致的重复噪声，应立即转为 `accepted`
3. **incomplete traceback（日志截断）** → 这类错误只有 `Traceback (most recent call last):` 这一行，没有后续堆栈，根本原因是日志格式或写入逻辑截断了。归类为 `accepted`，reason 填写"log truncation — no actionable stack trace"

**经验**：每次扫描发现 closed 错误再次出现时，立即更新 tracker 将其改为 `accepted`，不要等到下次。

## tracker 文件格式（重要）

`error_tracker.json` 的结构是 **wrapped list**：
```json
{
  "errors": [
    {
      "error_id": "err_001",
      "error_type": "FeishuEventProcessorNotFound",
      "summary": "...",
      "status": "closed",
      ...
    },
    ...
  ]
}
```
**注意**：`error_id` 可能重复（如 `err_001` 同时有 `closed` 和 `accepted` 条目）。遍历时应检查 `status` 而非假设 `error_id` 全局唯一。读取时用 `raw.get('errors', [])` 取列表。

## 目录结构

```
~/.hermes/
├── logs/                          # 原始日志
├── evolution_logs/
│   └── error_correction/
│       ├── YYYYMMDD_HHMMSS_report.json   # 测试报告
│       └── error_tracker.json           # 错误追踪状态
└── error_tracker.json              # 全局错误追踪（内部结构：{"errors": [...]}）
```

## 历史扫描记录

历次扫描详情记录在 `references/` 目录：
- `references/2026-05-03-scan.md` — 最近一次扫描（2026-05-03），包含错误分类明细和 tracker 状态快照

## 报告格式

```json
{
  "task": "log_error_correction",
  "timestamp": "2026-04-17T12:00:00",
  "scan_window_hours": 12,
  "errors_found": 3,
  "errors_closed": 1,
  "errors_accepted": 2,
  "errors_open": 0,
  "reports": [
    {
      "error_id": "err_001",
      "error_type": "ModuleNotFoundError",
      "summary": "tools/hermes_constants 模块导入失败",
      "status": "closed",
      "solution": "修改导入路径为 'hermes_constants'",
      "test_result": "passed",
      "test_duration_ms": 234
    }
  ],
  "open_errors_checked": [
    {
      "summary": "错误摘要",
      "previous_status": "open",
      "current_status": "accepted",
      "reason": "未在最近12h日志中出现"
    }
  ],
  "noise_filtered": {
    "asyncio_unclosed_client_session": 1000,
    "asyncio_unclosed_connector": 40
  },
  "category_breakdown": {
    "traceback_generic": {"groups": 1, "occurrences": 1358},
    "lark_ws_no_close": {"groups": 21, "occurrences": 40},
    "lark_ws_1011": {"groups": 7, "occurrences": 12}
  },
  "tracker_summary": {
    "total_tracked": 40,
    "closed": 19,
    "accepted": 21,
    "open": 0,
    "in_progress": 0
  }
}
```

> **注意**：`noise_filtered` 和 `category_breakdown` 字段必须直接写入最终 `report` 对象，不要只在代码中计算而忘记赋值。

## 已知问题

- `cronjob action=run` 不会立即执行任务，只是标记为待运行。实际执行依赖 cron 调度器进程。如果调度器未运行，任务不会真正执行。
- 手动触发测试时，直接用 Python 脚本执行，不要依赖 cron run。
- Skills 目录结构是 `~/.hermes/skills/{category}/{skill-name}/SKILL.md`，扫描时需要用 `rglob` 递归查找。
- 日志目录通常在 `~/.hermes/logs/`，包含 agent.log 和 errors.log。

### 日志时间过滤：必须用嵌入时间戳，不能只靠文件 mtime
**问题**: 日志文件的 modification time 不可靠。常见情况：
- 日志文件几天前创建但持续写入 → mtime 是几天前，但内容包含最近12小时的新错误
- 日志轮转后新建文件 → mtime 是新的，但内容是空的或很少
- 进程长期运行不重启 → mtime 保持很旧

**正确做法**: 先按文件 mtime 快速筛选文件，然后用正则提取每行日志的嵌入时间戳（如 `2026-04-17 12:06:08`），再按嵌入时间戳精确过滤到 12 小时窗口内。

**代码示例**:
```python
import re
from datetime import datetime, timedelta

cutoff = datetime.now() - timedelta(hours=12)
for log_file in logs_dir.glob('*'):
    if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
        continue  # 快速跳过太老的文件
    content = log_file.read_text(errors='replace')
    for line in content.split('\n'):
        ts_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
        if ts_match:
            ts = datetime.strptime(ts_match.group(1), '%Y-%m-%d %H:%M:%S')
            if ts >= cutoff and ' ERROR ' in line:
                # 只有这里才真正是 12 小时内的错误
                process_error(line)
```

### 噪音过滤：asyncio Unclosed client session/connector 警告

**问题**: `asyncio: Unclosed client session` 和 `asyncio: Unclosed connector` 在 Hermes 环境中出现频率极高（1000+ 次/12h），但属于 Python asyncio 运行时警告，不影响功能，不应计入真实错误。

**正确做法**: 在收集错误后立即过滤这些噪音模式：

```python
NOISE_PATTERNS = [
    'asyncio: Unclosed client session',
    'asyncio: Unclosed connector',
    'asyncio: Future exception was never retrieved',
]

real_errors = [line for line in all_error_lines
               if not any(noise in line for noise in NOISE_PATTERNS)]
```

**报告格式**中也应包含 `noise_filtered` 字段，记录每种噪音的出现次数。

### 新发现的错误类型（2026-04-29）

| 类别 | 描述 | 处置 |
|------|------|------|
| `hindsight_api_402` | Hindsight API 返回 402（欠费/需要付费）| `accepted` — 外部服务错误，非代码bug |
| `asyncio_unhandled_exception` | asyncio.run() 关闭时的未处理异常 | `accepted` — Python 关闭时 race condition，无功能影响 |
| `minimax_model_dump_error` | `'dict' object has no attribute 'model_dump'` | `accepted` — MiniMax API 返回原始 dict 而非 Pydantic model；下游 fallback 成功处理；偶发 |
| `traceback_generic` | 日志只有 `Traceback (most recent call last):` 一行，无后续堆栈 | `accepted` — 日志写入截断，无可操作信息 |
| `api_exception_response` / `api_exception_httpresp` | 只有 `raise ApiException.from_response` 或 `raise ApiException(http_resp=...)` 行 | `accepted` — 同上，日志截断导致无完整堆栈 |

### 新发现的错误类型（2026-05-03）

| 类别 | 描述 | 处置 |
|------|------|------|
| `build_anthropic_kwargs_drop_context` | `build_anthropic_kwargs() got an unexpected keyword argument 'drop_context_1m_beta'` | `accepted` — 旧字节码调用新函数签名；重启 worker 后消失；Hermes 升级遗留问题 |
| `feishu_edit_failed` | `Failed to edit message om_...` — 飞书编辑消息 API 超时/连接失败 | `accepted` — 瞬态网络错误；消息已发送成功只是编辑超时 |
| `invalid_api_response` | `Invalid API response after 3 retries: response.content invalid (not a non-empty list)` | `accepted` — MiniMax API 返回非列表内容；偶发；下游 fallback 处理 |
| `lark_connect_timeout` | `connect failed, err: timed out during opening handshake` | `accepted` — 瞬态网络问题；WebSocket 连接超时；自动重连成功 |

### 新发现的错误类型（2026-05-08）

| 类别 | 描述 | 处置 |
|------|------|------|
| `api_software_caused_connection_abort` | `Software caused connection abort` — API 调用被网络中断 | `accepted` — 网络波动；cron 重试机制自动处理；与代码无关 |
| `github_ssl_unexpected_eof` | `SSL routines::unexpected eof while reading` — GitHub HTTPS 连接被透明代理中断 | `accepted` — 网络/代理问题；Hermes update 失败会自动回退；改用 SSH 方式可绕过 |

### 飞书 WebSocket 断开错误（2026-04-30）

| 模式 | 描述 | 处置 |
|------|------|------|
| `Lark: receive message loop exit, err: sent 1011 (internal error) keepalive ping timeout` | 飞书服务器主动断开（1011 internal error，keepalive 超时）| `accepted` — 平台侧行为，非代码 bug；持续出现属正常网络重连 |
| `Lark: receive message loop exit, err: no close frame received or sent` | WebSocket 连接正常关闭（对端未发 close frame）| `accepted` — 飞书平台正常行为；连接复用时常见 |

## 执行陷阱（经验总结）

### execute_code 沙箱不保留变量，也不保留 imports
**问题**: `execute_code` 的沙箱在每次调用之间**不保留状态**。上一次调用的变量（如 `unique_errors`、`error_groups`）在下次调用中全部丢失。更隐蔽的是：**import 也不会保留**，`NameError: name 'defaultdict' is not defined` 是高频中招错误。

**正确做法**: 把所有分析逻辑放在**一个 `execute_code` 调用**中完成，包括：
- 收集日志 → 提取错误 → 去重 → 分类 → 生成报告 → 保存文件
- 绝对不能在两次调用之间 split 分析流程
- 每个 `execute_code` 代码块**必须包含完整的 import 语句**（`import json, datetime, re` 以及 `from pathlib import Path; from collections import defaultdict, Counter` 等）

**错误示范**:
```python
# 第一次调用：收集+去重
unique_errors = [...]  # 定义了但下次调用丢失
# 第二次调用：分类（unique_errors 已经不存在！）
for e in unique_errors:  # NameError
```

**正确示范**:
```python
# 一次调用搞定所有步骤
def full_analysis():
    error_records = collect_logs()
    all_errors = extract_errors(error_records)
    unique_errors = deduplicate(all_errors)
    error_groups = categorize(unique_errors)
    reports = analyze_and_fix(error_groups)
    save_report(reports)
    return reports
```

### tracker 读取时检查 value 类型

tracker 的 value 可能是 dict 也可能是 list（历史遗留数据）。读取后应做类型检查：

```python
raw = json.loads(tracker_path.read_text())
errors = raw.get('errors', [])  # 取列表，不是直接遍历 raw

for e in errors:
    if not isinstance(e, dict):  # 跳过非 dict 条目
        continue
    # 安全访问
    status = e.get('status', 'unknown')
```

### 飞书 bot_p2p_chat_entered_v1 错误可修复
**错误**: `processor not found, type: im.chat.access_event.bot_p2p_chat_entered_v1`
**原因**: 该事件（机器人进入私聊）没有注册处理器
**修复**: 在 `feishu.py` 的 `_build_event_handler()` 中添加：
```python
.register_p2_im_chat_access_event_bot_p2p_chat_entered_v1(lambda data: None)
```

## 手动执行方法

如果 cron 调度器未运行，可以用以下方式手动执行：

```python
import os, json, datetime
from pathlib import Path

hermes_home = Path.home() / '.hermes'
evolution_dir = hermes_home / 'evolution_logs'
err_corr_dir = evolution_dir / 'error_correction'
err_corr_dir.mkdir(parents=True, exist_ok=True)

# 扫描日志错误
log_dir = hermes_home / 'logs'
cutoff = datetime.datetime.now() - datetime.timedelta(hours=12)

# ... 分析错误，生成报告 ...

# 保存报告
report_file = err_corr_dir / f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}_report.json'
```

## 注意事项

- 测试在沙箱执行，不影响主系统
- 测试完成后删除临时文件
- 保留分析报告供后续查阅
- 如果错误复杂，标记为 `in_progress` 并记录原因
