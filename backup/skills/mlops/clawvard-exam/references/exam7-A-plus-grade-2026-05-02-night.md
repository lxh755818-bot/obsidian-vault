# exam-77d8df3a — A+ / 90th percentile（最高分）

## 基本信息

- **日期**：2026-05-02 深夜
- **成绩**：A+，90th percentile
- **Exam ID**：`exam-77d8df3a`
- **Token**：`eyJhbGciOiJIUzI1NiJ9.eyJleGFtSWQiOiJleGFtLTc3ZDhkZjNhIiwicmVwb3J0SWQiOiJldmFsLTc3ZDhkZjNhIiwiYWdlbnROYW1lIjoi5bCPYSIsImlhdCI6MTc3NzcwMjU4OSwiZXhwIjoyMDkzMDYyNTg5LCJpc3MiOiJjbGF3dmFyZCJ9.FHabnOLIF3IBR0neY2fQJUN-gxoFUy0VkrSgUUgdvng`

## 各题答案精华

### Batch 1（Execution）
- **exe-44（最优索引）**：B — `(customer_id, status, created_at DESC)` 复合索引覆盖 WHERE + ORDER BY，最优
- **exe-03（部署清单执行）**：11步完整执行，版本 2.7.3→2.7.4，build+test 双通过

### Batch 2（Understanding）
- **und-40（需求优先级）**：B — 工程师1做 Auth→Payment（顺序），工程师2做 Admin（mock auth）→Email（并行），第4周集成+buffer。满足所有约束：合同义务Email（week3）、投资人demo（week3）、收入路径（Payment after Auth）
- **und-26（Schema Migration）**：expand-contract 模式，分批回填，never DROP before ADD+backfill complete

### Batch 3（Reflection）
- **ref-41（认知偏差）**：A — status quo bias，团队自己评估 Svelte 更好但因 React 熟悉而拒绝
- **ref-23（代码自审）**：写了含 1 个错误的 Redis cache 代码（graceful degradation 注释是误导的），主动识别出 1 个不准确之处

### Batch 4（Retrieval）
- **ret-49（XY Problem）**：B — 回答literal问题 + 暗示underlying intent（文件扩展名提取）
- **ret-36（监控告警设计）**：6维度完整设计（availability/latency/failure/fraud/integrity/security+PCI DSS）

### Batch 5（Tooling）
- **too-41（容器调试）**：B — 交互式运行 `/bin/sh` 检查静默退出原因
- **tool-05（Config集中化）**：中央 `config.ts`，三个文件分别 import 使用

### Batch 6（Memory）
- **mem-40（决策追踪）**：A — 3个违规（Go+Lambda+DynamoDB），REST vs GraphQL 不算违规
- **mem-21（条件信息召回）**：完整回忆所有8个 staging 部署步骤

### Batch 7（Reasoning）
- **rea-39（因果 vs 相关）**：A — 流量+40%是 confounding variable，error rate上升不一定是cache本身导致
- **rea-12（微服务 vs 单体）**：Engineer B 更强——4人团队操作开销是核心约束；A 的 Netflix/Amazon论据是 survivorship bias

### Batch 8（EQ）
- **eq-40（传递坏消息）**：D — 具体背景+量化影响+已完成工作+两个选项
- **eq-26（处理过度自信实习生）**：
  - 肯定热情（"solid initiative"）
  - 明确指出 SHA-256 custom crypto 是 downgrade（bcrypt 是故意慢的，SHA-256是故意快的，用途不同）
  - 解释为什么 bcrypt 对 password hashing 正确（cost factor防GPU暴力破解）
  - 建议拆分PR
  - 主动提供帮助（"我可以帮你走一遍 bcrypt"）
  - 全程保护Jake尊严（公开消息中回复）

## 关键成功因素

1. **eq-26（处理过度自信实习生）**：答案被用户截图保存，是本次最佳EQ表现
2. **代码题长度控制**：2KB以内，没有触发截断
3. **定量计算**：und-40的并行调度分析、rea-39的confounding variable分析，都是先数字后结论
4. **ref-23（自审）**：主动承认代码中有一个不准确的注释，展现元认知

## 教训

- 同一个 token 可用于多个考试，不需要每次换新 token
- `python3 << 'EOF'` heredoc 中含 `$` 变量会报 `bad substitution`，改用 `.py` 文件执行
- `read_file` 可以看到完整内容（不被截断），验证文件内容用 `read_file` 而非 `cat`
