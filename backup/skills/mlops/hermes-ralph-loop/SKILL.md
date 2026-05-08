---
name: hermes-ralph-loop
description: "Hermes Ralph Loop — PRD 驱动的自主开发循环系统，融合控制论+多智能体协同+钱学森综合集成方法论。核心：主控(JUDGE)→执行(ACTOR)→评审(JUROR)→决策(TERMINATOR) 四环。"
trigger: "ralph|自主循环|PRD驱动|多任务迭代|多智能体协同"
category: mlops
---

# Hermes Ralph Loop v2

## 核心理念

> 融合 Ralph 模式（PRD驱动）+ AgenticControl（6角色控制论）+ 钱学森综合集成方法论（定性→定量）

**本质：把控制系统工程方法论应用到 AI Agent 开发循环。**

## 架构：四环控制结构

```
                    ┌──────────────────────────────────────┐
                    │         META-CONTROLLER              │
                    │   (钱学森：定性→定量 综合集成)        │
                    └──────────────┬───────────────────────┘
                                   │
              ┌────────────────────▼────────────────────┐
              │              JUDGE (主控)                  │
              │  读PRD → 选story → 发给ACTOR → 收集结果   │
              │  职责：SCENARIST + SELECTOR + DISPATCHER  │
              └────────────────────┬────────────────────┘
                                   │ dispatch
                    ┌──────────────▼────────────────────┐
                    │         ACTOR (执行器)              │
                    │  delegate_task → subagent →干活    │
                    │  输出：files + learnings + metrics  │
                    └──────────────┬────────────────────┘
                                   │ feedback
              ┌────────────────────▼────────────────────┐
              │         JUROR (评审)                      │
              │  分析learnings → 量化进度 → 策略建议       │
              │  EXPLORE? EXPLOIT? REDESIGN?             │
              └────────────────────┬────────────────────┘
                                   │ verdict
              ┌────────────────────▼────────────────────┐
              │       TERMINATOR (终止判决)               │
              │  收敛判断 → 终止/继续/重新设计           │
              │  钱学森：系统稳定性判定                   │
              └──────────────────────────────────────────┘
```

## Agent 角色详解

### JUDGE（主控 = SCENARIST + SELECTOR + DISPATCHER）

对应 AgenticControl 的 SELECTOR + SCENARIST：

```python
def judge_select_story(prd):
    """选最高优先级且 passes:false 的 story"""
    pending = sorted(
        [s for s in prd["userStories"] if not s.get("passes", False)],
        key=lambda s: s.get("priority", 999)
    )
    return pending[0] if pending else None
```

**钱学森方法论映射：** JUDGE 负责"定性"阶段——理解需求、选方向。

### ACTOR（执行器）

```python
def actor_execute(story, prd):
    """调用 delegate_task，让 subagent 在目标 repo 干活"""
    prompt = build_actor_prompt(story, prd)
    result = delegate_task(
        goal=prompt,
        context=f"target_repo: {prd.get('targetRepo', '')}",
        toolsets=["terminal", "file", "web"]
    )
    return parse_actor_result(result)
```

**输出格式：**
```json
{
  "story_id": "US-001",
  "files_changed": ["models/task.py", "migrations/xxx.sql"],
  "learnings": ["用 alembic 管迁移", "Pydantic schema 需同步更新"],
  "passes": true,
  "attempt": 1
}
```

### JUROR（评审 = CRITIC + JUROR）

对应 AgenticControl 的 CRITIC + JUROR 合体：

```python
JUROR_STRATEGIES = {
    "EXPLORE": "宽范围测试，摸边界，不惜试错",
    "EXPLOIT": "在已知路径上深挖，最小化试错",
    "REDESIGN": "任务分解有问题，需要拆分成更小的 story"
}

def juror_review(iteration_history, current_learnings):
    """
    钱学森：综合集成方法论
    - 定量：量化进度（learnings 数量、文件变更量）
    - 定性：判断当前策略是否合适
    """
    strategy = infer_strategy(iteration_history)

    # EXPLORE → EXPLOIT 切换条件
    explore_ratio = iteration_history.explore_count / iteration_history.total
    if explore_ratio > 0.3 and iteration_history.stable_progress:
        strategy = "EXPLOIT"

    # REDESIGN 条件：连续 2 次迭代 learnings 为空 or 进度 <5%
    if is_stuck(iteration_history, last_n=2):
        strategy = "REDESIGN"

    return {
        "strategy": strategy,
        "reasoning": "...",
        "adjustments": ["建议缩小测试范围", "任务太大需拆分"]
    }
```

### TERMINATOR（终止判决）

对应 AgenticControl 的 TERMINATOR：

```python
TERMINATOR_THRESHOLDS = {
    "min_iterations_before_terminate": 3,   # 至少 3 次迭代才考虑终止
    "max_change_percent": 5,               # 参数/进度变化 ≤5%
    "max_zero_crossings": 5,               # （代码质量：零警告）
    "min_learnings_per_story": 1,           # 每个 story 至少 1 条 learning
}

def terminator_judge(iteration_history, prd):
    """
    钱学森：系统稳定性判定
    收敛 = 达到目标稳定状态
    """
    all_done = all(s.get("passes", False) for s in prd["userStories"])

    if all_done:
        return {"decision": "TERMINATE_SUCCESS", "reason": "所有 story 完成"}

    # 检查是否 stuck
    if is_stuck(iteration_history, last_n=3):
        return {"decision": "TERMINATE_STUCK", "reason": "连续3次无显著进展"}

    # 检查是否达到最大迭代
    if iteration_history.total >= TERMINATOR_THRESHOLDS["max_iterations"]:
        return {"decision": "TERMINATE_MAX", "reason": "达到最大迭代数"}

    return {"decision": "CONTINUE", "reason": "继续迭代"}
```

## PRD 格式 v2（量化版）

```json
{
  "project": "Hermes 记忆系统优化",
  "branchName": "ralph/memory-optimization",
  "description": "优化 Hermes 记忆检索精度",
  "targetRepo": "/data/data/com.termux/files/home/.hermes",
  "strategy": "EXPLORE",
  "userStories": [
    {
      "id": "US-001",
      "title": "添加 BM25 混合检索",
      "description": "在现有 FTS5 基础上增加 BM25 混合检索",
      "acceptanceCriteria": [
        "检索结果召回率提升 ≥15% (可测量)",
        "延迟 P99 <200ms (可测量)",
        "通过 pytest test_rag.py",
        "无 lint 错误"
      ],
      "priority": 1,
      "passes": false,
      "notes": "",
      "attempt": 0,
      "learnings": []
    }
  ]
}
```

**关键改进：acceptanceCriteria 必须量化（可测量），不能有模糊描述！**

## Progress Log v2（量化版）

```json
{
  "iterations": [
    {
      "id": "US-001",
      "attempt": 1,
      "strategy": "EXPLORE",
      "files_changed": ["search/bm25.py"],
      "learnings_count": 3,
      "passes": false,
      "reason": "召回率提升 8%，未达 15% 目标，继续 EXPLORE"
    }
  ],
  "total_iterations": 1,
  "current_strategy": "EXPLORE",
  "juror_recommendations": ["缩小参数搜索范围到 top-100"]
}
```

## 主循环流程

```python
def ralph_main_loop(prd_path):
    prd = load_prd(prd_path)
    history = load_history(prd_path)
    iteration = 0

    while True:
        iteration += 1
        print(f"\n=== Iteration {iteration} ===")

        # 1. JUDGE: 选 story
        story = judge_select_story(prd)
        if not story:
            print("所有 story 完成"); break

        # 2. JUROR: 评审 + 给出策略
        verdict = juror_review(history, None)
        print(f"策略: {verdict['strategy']} — {verdict['reasoning']}")

        # 3. ACTOR: 执行
        print(f"执行: {story['id']} - {story.get('title', '')}")
        result = actor_execute(story, prd, strategy=verdict["strategy"])

        # 4. JUROR: 评审结果
        verdict = juror_review(history, result)
        print(f"JUROR: {verdict['strategy']} — {verdict.get('adjustments', [])}")

        # 5. 更新状态
        update_prd(prd, result)
        append_progress(result)
        distill_to_memory(result["learnings"])

        # 6. TERMINATOR: 判决
        decision = terminator_judge(history, prd)
        print(f"TERMINATOR: {decision['decision']} — {decision['reason']}")

        if decision["decision"].startswith("TERMINATE"):
            handle_termination(decision, prd)
            break

        sleep(2)
```

## 与原版 Ralph 的区别

| 特性 | 原版 Ralph | Hermes Ralph Loop v2 |
|------|-----------|-------------------|
| 调度方式 | 手动写 while 循环 | JUDGE 自动调度 |
| 策略切换 | 无 | EXPLORE→EXPLOIT 自动 |
| 评审角色 | 无 | JUROR 每次评审 |
| 终止条件 | 简单 passes:true | 量化阈值（5%改善）|
| 学习沉淀 | 手写 progress.txt | distill_to_memory() |
| 记忆系统 | 文件 | Hermes 记忆宫殿 |
| 控制论映射 | 无 | 完整四环控制结构 |

## 坑点提醒

1. **每个 story 足够小** — 保证一次迭代能完成，US-001 应该就是"添加 BM25 检索"这么细，不是"优化记忆系统"
2. **acceptanceCriteria 必须量化** — 钱学森：定性→定量，不可量化就无法控制
3. **JUROR 是核心** — 策略切换判断，全靠 JUROR
4. **TERMINATOR 要有最小迭代保护** — 至少 3 次才考虑终止，防止过早退出
5. **learnings 不可为空** — 如果 subagent 返回空 learnings，说明 story 太简单或者没认真做

## 文件结构

```
~/.hermes/ralph/
├── ralph_loop.py          # 主循环（四环控制）
├── prd.json.example       # 量化版 PRD 格式
└── archive/              # 历史归档

~/.hermes/scripts/
├── ralph_iteration.py    # 单次迭代逻辑（v1兼容）
├── ralph_juror.py        # JUROR 评审逻辑
└── ralph_terminator.py   # TERMINATOR 判决逻辑
```
