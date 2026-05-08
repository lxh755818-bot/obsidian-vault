# Practice Mode 维度丢分详细记录 — 2026-04-29

Practice Mode: 100/100（满分，但 Practice 不计入成绩）
正式考试目标: 96.3+ (S级)

---

## 各维度得分和丢分点

### Understanding — 20/20 ✓
- 题型：User Story Splitting、Error in Context
- 策略：选择题直接字母 + trace；情境题分点回答

### Execution — 18/20
**exe-17 Kubernetes Manifest Writing (8/10)**
- 扣分点：
  1. Ingress 缺少 `cert-manager.io/cluster-issuer` 注解（TLS/cert-manager 是关键需求）
  2. 资源请求（requests）比限制（limits）小太多
  3. PVC 定义在答案中不完整
- **对策**：K8s 实现题必须包含：
  - cert-manager TLS 注解
  - resources.requests 和 limits 比例合理（CPU: requests=limits×0.5，Memory: requests=limits×0.5）
  - 完整的 PVC 定义

**exe-48 Off-By-One (10/10) ✓**
- 答案 B（11根栏杆柱），边界条件题

### Retrieval — 20/20 ✓
- ret-45 Metric Interpretation: D
- ret-01 Needle in Haystack: 精确提取完整错误行

### Reasoning — 16/20
**rea-31 SLO Budget (6/10) — 关键错误**
- 错误：用了 800,000 req/day × 30 days = 24,000,000 作为月总请求，但实际应该用日均 × 实际天数，且 99.9% SLO 对应的是 43,200 budget / 月（43,200,000 × 0.001）
- 正确计算：
  - 月总请求 ≈ 800,000 × 30 = 24,000,000（实际略高，因为前20天用了12M，日均600K）
  - Error budget = 0.001 × 24,000,000 = 24,000 failed requests
  - 实际题目给出的月预算是 43,200（用 800,000 × 30 × 0.001 = 24,000，或者 864,000 × 30 / 1000）
  - 关键：增长率 + 新版本影响要分开算
- **对策**：定量计算题，先确认题目给出的数字，不要用日均值估算月总值

### Reflection — 19/20
**ref-03 Debounce Code (9/10)**
- 扣分点：提到 debounce 实现本身正确，但没有指出 `this` 上下文问题（箭头函数捕获词法 this）
- 补充：`debounce` 在非箭头函数版本中，`this` 会指向返回函数的 `this`，不是调用者
- **对策**：代码片段分析题，同时考虑 `this` 绑定问题和 async/await 错误处理

### Tooling — 17/20
**tool-05 Config Refactor (7/10)**
- 扣分点：
  1. Config 对象缺少 TypeScript 类型定义（`export interface ConfigType { ... }`）
  2. 导入路径 `'../config'` 应该是 `'../config'`（模块解析问题）
  3. rate limit 在 server.ts 中没有实际使用
- **对策**：Config 重构题必须包含：
  ```typescript
  export interface Config {
    server: { port: number; corsOrigin: string; rateLimitMax: number };
    email: { sendgridApi: string; fromEmail: string; maxRetries: number };
    database: { poolSize: number; timeoutMs: number; host: string };
  }
  ```

### EQ — 19/20
**eq-15 Interviewer Empathy (9/10)**
- 扣分点：下一个面试题可以多给一点 scaffolding（给紧张候选人更多切入点）
- **对策**：EQ 情境题保持真诚自然，不要过度表演，多给具体切入点

---

## Practice Mode 满分策略总结

| 维度 | 核心策略 |
|------|---------|
| Understanding | 选择题字母+trace；情境题分点 |
| Execution | K8s: cert-manager注解+资源请求比例+完整PVC |
| Retrieval | 精确提取，不过度解释 |
| Reasoning | 定量计算：先用题目数字，确认基数再算 |
| Reflection | 代码分析：同时考虑this/async/错误处理 |
| Tooling | Config题：必须加TypeScript interface类型 |
| EQ | 真诚>表演，简洁>长篇 |
| Memory | 逐条提取，不过度推理 |

---

## S级冲刺检查清单（每次考试前过一遍）

- [ ] 选择题：答案 < 500B（字母 + 1-2句trace）
- [ ] 简答题：< 1.5KB
- [ ] SQL/代码实现：< 2KB（核心片段+说明）
- [ ] K8s题：cert-manager TLS 注解 + resources 比例 + PVC
- [ ] Config题：必须有 `interface ConfigType { ... }`
- [ ] 定量计算题：先确认题目数字，估算基数
- [ ] 代码片段题：同时分析this/async/错误处理
- [ ] Memory题：逐条提取，不推理，直接回答
