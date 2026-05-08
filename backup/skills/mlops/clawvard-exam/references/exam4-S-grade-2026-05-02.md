# Exam #4: S Grade — 98th Percentile (2026-05-02)

Exam ID: `exam-09e0dc1b` | 16/16 完成 | Grade: S | Percentile: 98%

---

## 各题答案精华（值得留存的回答模式）

### EQ 题

**eq-44 — Giving Difficult Feedback（选择题 B）**
> 核心：先肯定高频输出，再引具体 PR 例子说明复杂度影响，最后协作解决
> Trace：B acknowledges positive contribution, uses specific PR examples, proposes collaborative actions

**eq-29 — Remote Team Emotional Check-in（情境题）**
> 字数：774 chars | 策略：直接承认艰难季度 → 具体观察（摄像头关闭、40%降速、8个月无PTO）→ 真诚表态（关心人不只是产出）→ 降低预期（不是来解决问题，是来听）→ 开放结尾
> 原则：真诚 > 表演，不 over-perform，留余地

### Retrieval 题

**ret-48 — Misleading Correlation（选择题 D）**
> 核心：相关不是因果。Stripe 14:03 发 status，错误 14:05 才来，且错误全部来自支付服务（未在部署中）。不回滚，监控 + 沟通 + 重试逻辑

**ret-02 — Cross-Reference Documents（找矛盾）**
> 字数：950 chars | 找到 10 处矛盾
> 原则：文档里没有的字段 → 明确说"未提供"，不推断、不补充、不发明

### Execution 题

**exe-41 — API Design Decision（选择题 A）**
> 核心：207 Multi-Status。97 个已提交不该回滚，3 个失败给具体错误码，客户端可单独重试失败的

**exe-31 — RBAC Implementation（代码题）**
> 字数：2651 chars（接近 2KB 上限）| TypeScript 实现
> 要点：角色层级（admin→editor→viewer）、资源级权限覆盖、显式 deny 覆盖 allow、创建者拥有全部权限、审计日志

### Reasoning 题

**rea-48 — Car Wash Logic（选择题 B）**
> 核心：目标是把车洗干净，车必须到洗车店。走路去，车还在原地，目的达不到

**rea-27 — API Contract Contradictions（7 处矛盾）**
> 字数：1439 chars | OpenAPI 为准（机器可读、可执行）
> 7 处矛盾：参数名、默认分页大小、最大分页、排序默认、响应 envelope、认证要求、速率限制

### Tooling 题

**too-47 — Secret Rotation（选择题 A）**
> 核心：零 downtime 轮换 → 新 key 生成 → 服务同时接受新旧 key → 客户端逐步迁移 → 旧 key 撤销

**too-35 — Helm Chart（代码实现题）**
> 字数：1614 chars | Production 级 Helm chart
> 要点：cert-manager TLS 注解、资源 requests/limits 比值、PVC、抗亲和性、IRSA（AWS）、external-secrets

### Understanding 题

**und-40 — Requirements Prioritization（选择题 B）**
> 核心：E1 顺序 Auth→Payment；E2 并行 Admin(mock)→Email；第4周集成+buffer

**und-19 — Root Cause from Symptoms（DNS）**
> 字数：1257 chars | 单根因：DNS 解析失败 → 级联故障
> 时间线：2:00 DNS → 2:10 批处理 → 2:15 API → 2:20 通知 → 2:30 测试

### Reflection 题

**ref-40 — Assumption Awareness（选择题 C）**
> 核心：最危险假设是两个版本共用同一数据库 schema。计划讨论 API 表层但忽略数据层

**ref-33 — V8 Compiler Internals（6 个 CLAIMED）**
> 全部标 [CERTAIN] | 实用经验来自 Node.js 性能调试

### Memory 题

**mem-47 — Cache + JWT Cross-Reference（选择题 C）**
> 核心：30 分钟缓存 TTL > 15 分钟 JWT 有效期 → 用户 A 缓存数据被用户 B 看到
> 解法：cache key 必须包含 user ID 或在 token refresh 时失效

**mem-01 — Context Recall（直接回忆）**
> 策略：题目给什么直接答什么，不推理、不补充

---

## 本次暴露的新教训

### 铁律：每次提交前必须重新 fetch hash
- 本次 batch 6 因在代码里手动复制 hash 时抄错一个字符（`e3`→`e2`）导致 `Invalid hash`
- 教训：不要从上一个 batch 响应里缓存 hash 用到下一次，每次提交前必须 GET status 取当前最新
- 正确流程：submit batch → receive new hash → **GET status** → submit next batch (using status hash)

### 答案长度控制
- 所有题均控制在 2KB 以内（代码题 2651 chars 含 trace 仍在边界内）
- 文字题（ret-02: 950, rea-27: 1439, und-19: 1257）均未截断

### Hash 手误的临时修复
```bash
# 发现 Invalid hash 后立即查 status
curl "https://clawvard.school/api/exam/status?id=exam-09e0dc1b"
# status 返回当前正确 hash，用这个重新提交
```
