# reporter.py 崩溃诊断参考

## 症状

```
reporter.py rc=1
STDERR: Traceback (most recent call last):
  File "...reporter.py", line 416, in <module>
    run()
    ~~~^^
  File "...reporter.py", line 400, in run
    path, content = save_report(fmt)
                    ~~~~~~~~~~~^^^^^
  File "...reporter.py", line 366, in save_report
    content = format_cli_
```

rc=1，stderr 截断到 ~300 字符不足以定位根因。

## 已知表现

- skill-cycle-optimizer 触发 reporter.py 后，每次都崩溃
- 错误发生在 `format_cli_` 阶段（line 366）
- skill_optimizer 本身的 `Bug 19` 记录了这个现象，但未根治

## 诊断步骤（每次手动执行）

### 步骤 1：运行 reporter.py 并捕获完整 stderr

```python
import subprocess, sys
from pathlib import Path

LOG = Path.home() / ".hermes/evolution_logs" / "skill_optimizer"
r = subprocess.run(
    [sys.executable, str(LOG / "reporter.py")],
    capture_output=True, text=True, timeout=60
)
print(f"rc={r.returncode}")
print("STDERR:\n", r.stderr)
print("STDOUT:\n", r.stdout[:500] if r.stdout else "(empty)")
```

### 步骤 2：直接查看 reporter.py 相关行

reporter.py 在 line 366 的 `format_cli_` 函数中崩溃：
- 读取 `~/.hermes/evolution_logs/skill_optimizer/reporter.py` 的 line 360-416
- 检查 `save_report()` 调用链：`run() → save_report(fmt) → format_cli_`
- 检查 trends.json 和 skill_history.json 是否存在、schema 是否兼容

### 步骤 3：常见根因

| 根因 | 表现 |
|------|------|
| trends.json schema 不一致 | `format_cli_` 读取旧 schema 记录时报 KeyError |
| skill_history.json 缺失 | `get_passing_rate()` 等函数访问不存在的文件 |
| Jinja2/slate 模板渲染失败 | `format_cli_` 内部模板变量缺失 |

### 步骤 4：快速验证方法

```python
import json
from pathlib import Path

LOG = Path.home() / ".hermes/evolution_logs" / "skill_optimizer"
# 检查文件是否存在
for f in ["trends.json", "skill_history.json"]:
    p = LOG / f
    print(f"{f}: exists={p.exists()}, size={p.stat().st_size if p.exists() else 0}")

# 检查 trends.json 最后一条记录 schema
with open(LOG / "trends.json") as f:
    t = json.load(f)
if t["records"]:
    last = t["records"][-1]
    print("Last trend record keys:", list(last.keys()))
    print("Has 'current' key:", "current" in last)
```

## 已知 Bug 对应

- **Bug 10**: trends.json 混用新旧 schema，导致读取失败
- **Bug 19**: stderr 截断，错误被静默忽略

## 修复方向

1. `reporter.py` 需要更好的错误捕获：`except Exception as e` 时输出完整 traceback 到日志文件
2. skill-cycle-optimizer 应在 reporter.py 失败后记录完整错误（不受截断限制）
3. 长期：统一 trends.json schema，废弃旧 schema

## 状态

> ⚠️ 截至 2026-05-08 此问题仍未解决。每次 skill-cycle-optimizer 运行，reporter.py 均 rc=1。DOJO 闭环其他 5/6 模块正常工作。
