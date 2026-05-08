# 自我进化系统 — 参考资料

## 四环控制架构（Ralph Loop 实现）

本 session 落地了自我进化系统"反馈层"的完整实现，基于三项研究：

### 1. Ralph 模式（GitHub: snarktank/ralph, iannuttall/ralph）

**核心思路**：PRD 拆小任务 + 文件传信息 + 主调度 + 子智能体分工

**关键机制**：
- 每次迭代 spawn 新 AI 实例（上下文清空），只通过文件共享状态
- `prd.json` 任务清单 + `progress.txt` learnings 追加
- 单故事提交：每轮迭代完成一个 story 并 commit

**文件**：
- `~/.hermes/ralph/ralph.sh` — 原版 Ralph bash 循环
- `~/.hermes/ralph/CLAUDE.md` / `prompt.md` — 子 agent prompt 模板

---

### 2. AgenticControl (arXiv:2506.19160)

**6 角色控制论**：ACTOR / CRITIC / TERMINATOR / SELECTOR / SCENARIST / JUROR

**核心贡献**：
- **EXPLORE → EXPLOIT 策略切换**：前 30% 迭代宽范围探索，后 70% 在最优路径深挖
- **量化终止条件**：参数变化 ≤5%、最小 6 次迭代保护
- **JUROR 动态调参**：根据探索进度建议调整参数范围

**量化阈值（已实现）**：
```
min_iterations_before_terminate: 3
max_change_percent: 5
max_iterations: 50
min_learnings_per_story: 1
```

---

### 3. 钱学森控制论（《系统与控制纵横》2014）

**核心公式**：
```
控制 = 测量（反馈）→ 比较 → 调整 → 再测量（循环）
```

**套用到 AI Agent 循环**：
| 控制系统 | AI Agent 对应 |
|---------|--------------|
| 被控系统 | PRD（要达成的目标）|
| 反馈信号 | progress.txt learnings |
| 比较器 | JUROR |
| 调整策略 | EXPLORE/EXPLOIT |
| 稳定性判定 | TERMINATOR |

**关键洞察**：
- 钱学森："由于复杂因素的错综复杂影响，**智能化的方法是不可避免的**"
- 综合集成方法论：从定性到定量，不可量化就无法控制

---

## 落地实现

### 四环控制结构

```
JUDGE → ACTOR → JUROR → TERMINATOR

JUDGE:   读PRD → 选story → 发给ACTOR
ACTOR:   delegate_task → subagent → 产出 files + learnings
JUROR:   分析learnings → 量化进度 → 策略建议（EXPLORE/EXPLOIT/REDESIGN）
TERMINATOR: 收敛判断 → 终止/继续/重新设计
```

### 文件清单

```
~/.hermes/scripts/
├── ralph_iteration.py   (306行，主循环，四环控制)
├── ralph_juror.py       (JUROR 评审 + 策略切换)
├── ralph_terminator.py  (TERMINATOR 量化判决)
└── ralph_new_prd.py     (PRD 生成器)

~/.hermes/ralph/
├── ralph              (CLI 入口：new/status/run/log/archive)
├── ralph.sh           (原版 Ralph bash 循环参考)
├── prd.json.example   (量化版 PRD 格式)
└── archive/           (历史归档)

~/.hermes/skills/mlops/hermes-ralph-loop/
└── SKILL.md          (v2 完整架构文档)
```

### PRD 量化格式关键要求

```json
{
  "acceptanceCriteria": [
    "可量化标准（如 召回率≥15%）",   // ✅
    "通过 pytest 测试",              // ✅
    "用户体验提升"                   // ❌ 禁止模糊
  ]
}
```

### JUROR 策略切换逻辑

```python
EXPLORE → 条件：learnings < 3 条 or 迭代数 < 总数的 30%
EXPLOIT → 条件：总 learnings ≥ 3 and 迭代过半
REDESIGN → 条件：连续 2 次 learnings ≤ 1（stuck）
```

### TERMINATOR 判决逻辑

```python
TERMINATE_SUCCESS:  所有 passes:true
TERMINATE_STUCK:   连续 3 次无实质进展
TERMINATE_MAX:     达到 50 次迭代
CONTINUE:          未达终止条件
```

---

## 与 hermes-dojo 的架构重叠

hermes-dojo-integration 的 Monitor→Analyzer→Fixer→Reporter 与本架构的 JUROR/TERMINATOR 功能高度重叠：

| hermes-dojo | Ralph Loop |
|------------|-----------|
| Monitor（采集信号）| JUROR（评审进度）|
| Analyzer（动态评分）| JUROR（策略决策）|
| Fixer（执行修复）| ACTOR（执行story）|
| Reporter（日报）| progress.txt 追加 |

**建议**：后续可将 hermes-dojo 的 Fixer/Reporter 角色接入 Ralph Loop，统一为四环结构。
