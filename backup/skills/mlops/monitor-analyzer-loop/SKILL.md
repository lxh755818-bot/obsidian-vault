---
name: monitor-analyzer-loop
description: 构建 Monitor + Analyzer 失败信号采集与决策闭环。从 trends.json 和 error_ledger.md 双源采集信号，动态计算评分，输出优先级改进决策。hermes-dojo 的 measure→identify 闭环复现。
version: 1.0.0
author: 小a
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [Self-Evolution, Error Analysis, Skill Improvement]
    category: mlops
---

# Monitor + Analyzer 失败信号决策闭环

## 背景

这是 hermes-dojo 的 measure→identify 闭环在我们系统的复现：
- **Monitor**：采集失败信号（trends.json 测试结果 + error_ledger.md 错误记录）
- **Analyzer**：将信号转化为优先级改进决策（动态评分，不依赖静态配置）

## 核心价值

```
trends.json（测试结果） ──┐
                          ├──► Monitor ──► failure_signals.json
error_ledger.md（错误） ──┘         │
                                    ▼
                         Analyzer ──► improvement_plan.json
```

## 文件位置

```
~/.hermes/evolution_logs/skill_optimizer/
├── monitor.py              # Monitor 模块
├── analyzer.py             # Analyzer 模块（v2 动态评分）
├── failure_signals.json    # Monitor 输出
└── improvement_plan.json   # Analyzer 输出
```

## v2 动态评分公式

```
score = frequency × impact × auto_fix_potential

decision:
  score > 8 + runtime_error  → deep_review（深度检修）
  score > 8                  → new_skill（生成新技能）
  score 4-8                  → add_rule（加入规则集）
  score < 4                  → archive（归档监控）
```

### frequency（1-5）
基于测试次数 + 失败率，失败率越高乘数越大（1.0~1.5）

### impact（1-5）
基于失败类型 + 是否核心技能：
- runtime_error → 5（影响最大）
- dep_missing → 4
- doc_fail → 3
- 核心技能加权 +1

### auto_fix_potential（0.5-2.0）
- doc_fail only → 1.8（最易修复）
- dep_missing → 0.8
- runtime_error → 0.5（最难修复）

## 关键 Bug：defaultdict.get() 的陷阱

**问题**：`defaultdict(int)` 调用 `.get(key)` 返回 `None` 而非 `0`，导致 `TypeError: '>' not supported between 'NoneType' and 'int'`。

```python
# ❌ 错误：empty defaultdict.get() 返回 None
if failure_types.get("runtime_error") > 0:  # TypeError!

# ✅ 正确：用 or 0 或自定义 helper
if failure_types.get("runtime_error") or 0 > 0:

# 或定义 helper
def _ft_get(d: dict, key: str) -> int:
    return d.get(key) or 0
```

## 关键 Bug：双数据源信号不一致

**问题**：trends.json 显示 `failed=0` 但 error_ledger 有错误记录，导致 failure_types 存在但 failed=0。

**根因**：Monitor 的两个数据源采集时间窗口不同步，导致同一技能在一个源有记录、在另一个源没有。

**修复**：在 `compute_frequency()` 中合并两个源的信号：
```python
has_ft = any((failure_types.get(k) or 0) > 0 for k in failure_types)
effective_failed = max(failed, 1 if has_ft else 0)
effective_total = max(total, 1)
failure_rate = effective_failed / effective_total
```

## 调用方式

```bash
python ~/.hermes/evolution_logs/skill_optimizer/monitor.py
python ~/.hermes/evolution_logs/skill_optimizer/analyzer.py
```

或集成进 skill-cycle-optimizer 的每轮测试后。

## 局限性

1. **error_ledger.md 格式依赖**：Monitor 用正则解析 `## [TIMESTAMP]` 条目，格式变化则解析失效
2. **failure_types 分类粗糙**：目前只有 doc_fail / dep_missing / runtime_error 三类，实际错误可能更复杂
3. **评分阈值靠经验**：score > 8 / 4-8 / < 4 的阈值未经充分验证
4. **Fixer 未实现**：Analyzer 只输出决策，不执行修复

## 下一步：Fixer 闭环

Analyzer 输出决策后，需要 Fixer 执行：
- `new_skill` → 生成新 skill 或大幅重构
- `deep_review` → 输出具体修复建议，附验证步骤
- `add_rule` → 写入 HEARTBEAT.md 或 skill 规则章节
- `archive` → 降低监控频率
