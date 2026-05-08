---
name: hermes-dojo-integration
description: 从 hermes-dojo（GitHub Yonkoo11/hermes-dojo）架构出发，嫁接 Monitor + Analyzer + Fixer + Reporter 到 Hermes skill-cycle-optimizer 的完整方法论。包含踩坑记录、动态评分设计思路、文件架构。
version: 1.0.0
author: 小a
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [Self-Evolution, Skill-Testing, Monitoring, Cron]
    stability: stable
---

# hermes-dojo Integration Skill

## 概述

hermes-dojo（GitHub: Yonkoo11/hermes-dojo）是 Hermes Agent 的自我进化系统，核心反馈循环：

```
measure → identify weakness → evolve → measure again → report
```

本 skill 记录将其嫁接到现有 skill-cycle-optimizer + evolution-system 体系的完整方法，包含踩坑记录和动态评分设计。

---

## 嫁接架构

```
数据源:
  trends.json（skill-cycle-optimizer 测试结果）
  error_ledger.md（错误日志）

        ↓
┌───────────────────┐
│     Monitor       │  采集失败信号，输出 failure_signals.json
│  monitor.py       │
└────────┬──────────┘
         ↓
┌───────────────────┐
│    Analyzer v2     │  动态评分，输出 improvement_plan.json
│  analyzer.py       │  score = frequency × impact × auto_fix_potential
└────────┬──────────┘
         ↓
┌───────────────────┐
│     Fixer v2      │  执行修复，输出 fixes_pending/
│  fixer.py          │  deep_review / new_skill / add_rule
└────────┬──────────┘
         ↓
┌───────────────────┐
│    Reporter       │  生成日报: CLI / JSON / 飞书卡片
│  reporter.py      │
└───────────────────┘
```

---

## 目录结构

```
~/.hermes/evolution_logs/skill_optimizer/
├── monitor.py              # Monitor 模块
├── analyzer.py             # Analyzer v2（动态评分）
├── fixer.py               # Fixer v2（执行修复）
├── reporter.py             # Reporter（日报生成）
├── dojo.py                # 一键执行完整闭环
├── failure_signals.json    # Monitor 输出
├── improvement_plan.json   # Analyzer v2 输出
├── fixes_pending/          # Fixer 输出（待审批）
│   ├── _fixer_summary_v2.json
│   ├── <skill>_diag_v2.json    # 深度检修诊断
│   └── <skill>_fix_v2.json     # 文档修复方案
└── reports/               # 历史日报
```

---

## 文件职责

### monitor.py
- 扫描 `trends.json`（skill-cycle-optimizer 测试结果）和 `error_ledger.md`（错误日志）
- 输出 `failure_signals.json`，包含 severity、signal_type、count
- 时间窗口：48小时

### analyzer.py v2
- 核心：动态评分，不依赖静态配置
- `score = frequency × impact × auto_fix_potential`
  - frequency: 从 trends.json 计算测试次数 + 失败率
  - impact: 从失败类型（doc_fail / dep_missing / runtime_error）+ 核心技能加权
  - auto_fix_potential: doc_fail=1.8（易修），runtime_error=0.5（难修）
- decision: `deep_review` / `new_skill` / `add_rule` / `archive`
- 关键 bug：**`defaultdict.get()` 返回 `None` 而非默认值 0**，必须用 `or 0` 补救

### fixer.py v2
- `deep_review`: 诊断依赖（Python库 + CLI工具），输出 `*_diag_v2.json`
- `new_skill`: 检查文档完整性，区分"文件已修复"vs"真正通过"
- `add_rule`: 写入 HEARTBEAT.md
- 依赖检查：过滤内部模块（GapAnalyzer、hermes_tools 等）和版本号形式的依赖

### reporter.py
- CLI 日报：带 emoji 状态图标（🟢🟡🔴）
- JSON 格式：含 trends + plan + fixes_pending
- 飞书卡片：lark-oapi post 格式

### dojo.py
- 一键执行：Monitor → Analyzer → Fixer(dry-run) → Reporter
- 可选飞书推送

---

## 踩坑记录（重要）

### Bug 1: defaultdict.get() 返回 None（analyzer.py）

**问题**: `failure_types = defaultdict(int)`，调用 `failure_types.get("runtime_error")` 返回 `None` 而非 `0`。

**错误代码**:
```python
if failure_types.get("runtime_error") > 0:  # TypeError: None > 0
```

**正确做法**:
```python
def _ft_get(d: dict, key: str) -> int:
    return d.get(key) or 0

if _ft_get(failure_types, "runtime_error") > 0:
```

### Bug 2: 正则字符集未闭合（fixer.py）

**错误**: `re.split(r"[><=!]", dep)` 中的 `!` 在字符集中需要转义或放在首位以外的位置，Python 3.13 报错 `unterminated character set`。

**正确做法**:
```python
re.split(r"[><=!]", dep)  # 正确
# 或者
re.split(r"[><=!]", dep)  # ! 单独处理
```

### Bug 3: skill-path 解析后不重置 content（fixer.py）

**问题**: `parse_frontmatter()` 返回 `fm, body`，但之后又重新打开文件读取 `content`，导致 body 和 content 不一致。

**正确做法**: 一次读取，三元返回：
```python
def parse_frontmatter(md_path: Path):
    content = md_path.read_text(errors="replace")
    if not content.startswith("---"):
        return None, None, content
    end_idx = content.find("\n---\n", 3)
    if end_idx == -1:
        end_idx = content.find("\n---", 3)
        if end_idx == -1:
            return None, None, content
    yaml_text = content[3:end_idx].strip()
    body = content[end_idx + 4:]
    try:
        fm = yaml.safe_load(yaml_text)
    except Exception:
        fm = None
    return fm, body, content
```

### Bug 4: skill-cycle-optimizer 自测时 failure_types 来自 error_ledger 但 failed=0

**问题**: error_ledger 记录了运行时错误，但 trends.json 的 `failed=0`，导致 failure_rate=0 但仍有 runtime_error 标记。

**正确做法**: `compute_frequency` 里对这种不一致做兜底处理：
```python
has_ft = any((failure_types.get(k) or 0) > 0 for k in failure_types)
effective_failed = max(failed, 1 if has_ft else 0)
```

### Bug 5: Fixer 扫描 body 里的 import 时混入中文注释

**问题**: `re.findall(r"(?:import|from)\s+(\w+)", body)` 匹配到中文注释里的乱码依赖名。

**正确做法**: 过滤非 ASCII 字符：
```python
deps = [d for d in deps if d and d.replace("_", "").replace("-", "").replace(".", "").isalnum() and d.isascii()]
```

---

## Analyzer v2 动态评分设计

### 数据来源优先级
1. trends.json 的 audit 字段（最准确）
2. error_ledger.md 的错误日志（辅助信号）
3. 静态配置的 core_skill 列表（兜底）

### 评分公式
```
score = frequency × impact × auto_fix_potential

frequency:
  - 测试次数: 1-5 分（1次=2分, 2次=3分, 3次=4分, 5次+=5分）
  - 失败率放大: ≥80%失败率 → ×1.5, ≥50% → ×1.2

impact:
  - runtime_error: 5（影响最大）
  - dep_missing: 4
  - doc_fail: 3
  - 核心技能额外 +1

auto_fix_potential:
  - doc_fail 且无 runtime_error: 1.8（文档最易修）
  - dep_missing: 0.8
  - runtime_error: 0.5（最难修）

decision:
  score > 8 + runtime_error → deep_review
  score > 8 + doc_fail    → new_skill
  score 4-8                → add_rule
  score < 4                → archive
```

---

## Cron 调度

```bash
# 每天 09:00 自动跑完整 dojo + 飞书推送
cronjob create \
  --name hermes-dojo-daily \
  --prompt "$(cat dojo.py)" \
  --schedule "0 9 * * *"
```

---

## 扩展方向

1. **Learning Curve**: 每天记录 health_score 到 `metrics.json`，画 sparkline
2. **Auto-Fix**: Fixer 的 `new_skill` decision 实际执行文档补丁（需 human review）
3. **动态 frequency/impact**: 从 trends.json 历史数据拟合，不靠人工配置 core_skill 列表
4. **飞书卡片推送**: 用 lark-oapi 发送真正的富文本消息，而不是纯文本

## 与 Hermes Ralph Loop 的架构整合

hermes-dojo 的 Monitor→Analyzer→Fixer→Reporter 与 Ralph Loop 的四环控制（JUDGE→ACTOR→JUROR→TERMINATOR）存在角色映射：

| hermes-dojo | Ralph Loop | 职责 |
|-------------|-----------|------|
| Monitor | JUROR | 采集信号，评审进度 |
| Analyzer | JUROR | 动态评分，决策策略 |
| Fixer | ACTOR | 执行修复/故事 |
| Reporter | progress.txt | 记录 learnings |

**整合建议**：Ralph Loop 的 JUROR/TERMINATOR 可直接复用 hermes-dojo 的 Analyzer/Fixer 逻辑，形成统一的自进化闭环。
