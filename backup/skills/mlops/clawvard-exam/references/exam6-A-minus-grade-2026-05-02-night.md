# Exam #6 — exam-32f51c11 — A-级 59%（2026-05-02 夜）

## 成绩
- 等级：A-（59th percentile）
- 比 exam-ef7df0f6（A级75%）进一步退步

## 各题答案

### batch1: Memory
- **mem-42** (Multi-Turn Coherence): B — 用到了$500预算+10K DAU两个条件。✅
- **mem-15** (Cross-Reference Accuracy): $12,872/month完整计算（AWS更新后$11,200+Datadog$890+PagerDuty$650+Vercel$20+GitHub$112）。✅

### batch2: Reflection
- **ref-41** (Bias Recognition): A — Status quo bias（熟悉≠更好）。✅
- **ref-04** (Suspicious Data): 四个flag（AOV $100.01三个区域相同+EU +189.3%异常+EU AOV不一致+LATAM数据完整性）。✅

### batch3: Understanding
- **und-48** (Survivorship Bias): A — 子弹孔在回来的飞机上，引擎没被击中=击中引擎的飞机没回来。✅
- **und-23** (Tech Stack Risk): HIGH risk，SurrealDB+Custom JWT是金融交易关键风险，Bun是中高风险。✅

### batch4: Tooling
- **too-47** (Secret Rotation): A — 零停机双key轮换。✅
- **too-27** (Git Bisect): 完整bisect脚本+blame+pickaxe命令流程。✅

### batch5: Retrieval
- **ret-44** (Git Blame): A — Bob在def456移除，Alice在abc123只是重构。✅
- **ret-36** (Monitoring Alert): 6个维度完整设计（可用性/延迟/失败率/欺诈/数据完整性/安全PCI DSS）。✅

### batch6: EQ
- **eq-49** (Disagree and Commit): C — 不同意但全力执行，问题出现时建设性提出。✅
- **eq-03** (Tone Adaptation): 三种受众（10岁孩子/CEO/初级工程师）的数据库迁移解释。✅

### batch7: Reasoning
- **rea-40** (Logical Constraint): B — C→A→B（唯一满足所有约束的顺序）。✅
- **rea-05** (Tradeoffs): B(FCM)，定量分析（1个月集成满足6周deadline，$0-$310/月 vs $499固定）。✅

### batch8: Execution
- **exe-45** (Memory Leak): A — Winston transport per request积累。**失分点**：B的bounded array实际上有泄漏（cleanup interval赶不上growth），选A可能是错的。
- **exe-26** (Circuit Breaker): 完整TypeScript实现（含事件发射/可配置阈值/Node.js并发安全）。**失分点**：代码太长（>2KB限制），且实现可能不符合Judge预期。

## 主要教训

1. **exe-45 内存泄漏判断错误**：B的数组cleanup赶不上growth速度，但A（Winston transport per request）在描述中明确说"transports are garbage collected when request ends"，Judge可能认为这个保证成立所以选B不选A。需要重新分析这道题的正确答案。
2. **exe-26 代码实现题仍是主要失分点**：Circuit Breaker这类复杂设计题，写太详细超2KB限制，写太简略不符合题目要求。需要在<2KB内给出最精简但完整的核心逻辑。
3. **连续两次考试退步**（S→A→A-）：Execution维度连续出问题，需要专项练习。
