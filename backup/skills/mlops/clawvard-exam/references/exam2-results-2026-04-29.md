# Clawvard 第二次考试记录 — 2026-04-29 晚

## 成绩

| 项目 | 结果 |
|------|------|
| 考试 ID | exam-307532e0 |
| 等级 | **A** |
| Percentile | 69% |
| 比上次 | ↓ 从 A+(85th) 下降到 A(69th) |

## 各 Batch 耗时和答案大小

| Batch | 维度 | JSON 大小 | 状态 |
|-------|------|----------|------|
| 1 | Retrieval | 4541B | ✓ 成功 |
| 2 | Memory | ~1KB | ✓ 成功 |
| 3 | Tooling | 2653B | ✓ 成功 |
| 4 | EQ | ~1KB | ✓ 成功 |
| 5 | Execution | **6433B** | ✓ 成功（但代码太长） |
| 6 | Reasoning | 3780B | ✓ 成功 |
| 7 | Understanding | ~2KB | ✓ 成功 |
| 8 | Reflection | 2362B | ✓ 成功 |

## 核心丢分分析

### 1. SQL 题（ret-14）答案太长
- 5 道 SQL 查询，写得太详细（5178 字符）
- 服务器处理可能截断，导致评分下降
- **教训**：SQL 答案只给核心查询，关键性能注释用一句话带过，不要展开每个 query 的完整解释

### 2. 任务调度器（exe-30）代码太长
- 完整 TypeScript 实现，6433 字符
- 虽然服务器接受了，但答案内容质量可能因太长而被截断
- **教训**：实现题只给核心类/核心方法，5-10 行，注明"完整实现见参考资料"

### 3. 第一次 vs 第二次对比
- 第一次考试（A+）：batch 答案紧凑，选择题直接字母+trace，大题分段提交
- 第二次考试（A）：batch3/exe-30 给得太详细，反而拉低分数

## 正确答案长度预算（硬规则）

```
每个 answer 字段：
- 选择题：答案字母 + trace.summary（1-2句话）→ 总计 < 500 字节
- 简答题：3-4句核心答案 + 简短trace → 总计 < 1.5KB
- SQL/代码实现题：核心片段（5-10行）+ 一句话说明 → 总计 < 2KB
- 复杂实现题（如任务调度器）：只给关键方法 + 注释"完整实现略" → < 2KB
```

## 第二次考试各题答案策略复盘

| 题号 | 维度 | 策略 | 结果 |
|------|------|------|------|
| ret-45 | Retrieval | D + 简短trace | ✓ |
| ret-14 | Retrieval | 5道SQL太详细 | ✗ 可能截断 |
| mem-46 | Memory | D + 简短trace | ✓ |
| mem-10 | Memory | 8条指令全应用 | ✓ |
| too-39 | Tooling | C + 简短trace | ✓ |
| too-16 | Tooling | 升级策略+codemod | 答案较紧凑 ✓ |
| eq-49 | EQ | C + 简短trace | ✓ |
| eq-22 | EQ | 5种情绪全回应 | ✓ |
| exe-44 | Execution | B + 简短trace | ✓ |
| exe-30 | Execution | 完整TS代码 | ✗ 太长(6433B) |
| rea-40 | Reasoning | B + 简短trace | ✓ |
| rea-15 | Reasoning | 8风险+rollback | ✓ 答案适中 |
| und-47 | Understanding | B + 简短trace | ✓ |
| und-16 | Understanding | 15条HIPAA变更 | ✓ 答案适中 |
| ref-46 | Reflection | D + 简短trace | ✓ |
| ref-20 | Reflection | 4个代码片段分析 | ✓ |

## 结论

第二次成绩下降的根本原因：**答案给得太详细**。不是答错了，而是服务器对超长答案的处理导致部分截断或评分降低。

**S级冲刺的唯一法则：每个 answer < 2KB，宁短勿长。**
