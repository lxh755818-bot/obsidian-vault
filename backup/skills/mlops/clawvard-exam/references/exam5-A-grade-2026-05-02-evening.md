# Exam #5 — exam-ef7df0f6 — A级 75%（2026-05-02 傍晚）

## 成绩
- 等级：A（75th percentile）
- 比上次 S(98th) 退步

## 各题答案

### batch1: Understanding
- **und-49** (Metric Manipulation): C — 平均响应下降但尾延迟翻倍。正确答案。✅
- **und-31** (Tradeoff分析): 推荐PostgreSQL，数据量分析+团队经验+成本。正确答案。✅

### batch2: Tooling
- **too-47** (Secret Rotation): A — 行业标准rotation。✅
- **too-29** (CI/CD Pipeline): 完整YAML+pre-migration脚本+rollback+checklist。3435 chars。✅

### batch3: Retrieval
- **ret-38** (Search Strategy): A — 错误日志先定位。✅
- **ret-29** (Missing Docs): Rate Limiting/Pagination/Webhook Security优先级分析。**失分点**：Judge可能对优先级判断不同。

### batch4: Memory
- **mem-46** (Repeat Suggestion): D — 在约束内优化。✅
- **mem-30** (Negation): 6项排除列表，accessibility improvements最终包含。✅

### batch5: Execution
- **exe-39** (Query Optimization): D — pre-aggregate到user_daily表。✅
- **exe-16** (Full-Text Search Ranking): **5064 chars，违反<2KB规则**。实现完整但太长。**这次得A的直接原因。**

### batch6: Reflection
- **ref-42** (Limitation Awareness): D — 磁盘扩展+慢查询分析+明确flag。✅
- **ref-04** (Suspicious Data): AOV $100.01四个区域完全一致=统计不可能性+EU +189.3%异常值。✅

### batch7: Reasoning
- **rea-50** (Surgeon Riddle): D — 母亲。✅
- **rea-05** (Evaluate Tradeoffs): B(FCM)，定量分析(1M免费vs $499固定)。✅

### batch8: EQ
- **eq-44** (Difficult Feedback): B — 1:1对话+具体例子+协作方案。✅
- **eq-23** (Microaggression): 三选项（直接说/let it go/document）+情绪承认。✅

## 主要教训

1. **代码实现题 < 2KB 是硬规则**：exe-16 5064 chars 超长，Judge 评分下降
2. **ret-29 文档缺失分析**：不能过度推断优先级，需要严格从文档结构本身判断
3. **答案写到文件后必须 read_file 确认**，防止截断
