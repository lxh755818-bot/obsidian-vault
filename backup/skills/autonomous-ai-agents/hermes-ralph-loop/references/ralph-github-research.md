# Ralph GitHub 调研摘要

## 热门仓库（按类型）

### 1. AI Agent Loop 类（本次重点）

**snarktank/ralph** ⭐ 主推
- 循环调用 Claude Code/Amp，PRD 驱动
- 每次迭代刷新上下文，文件共享状态
- `COMPLETE` 信号退出
- https://github.com/snarktank/ralph

**iannuttall/ralph**
- 更轻量的文件版，npm 包
- 架构：`.agents/ralph/` 模板 + `.ralph/` 状态 + `.agents/tasks/` PRD
- 支持 codex/claude/droid/opencode 多工具
- https://github.com/iannuttall/ralph

**PageAI-Pro/ralph-loop**
- Vercel AI SDK 风格的 long-running agent loop
- https://github.com/PageAI-Pro/ralph-loop

**vercel-labs/ralph-loop-agent**
- Ralph Wiggum technique（持续喂 AI 直到完成）
- https://github.com/vercel-labs/ralph-loop-agent

### 2. Learning Record Store 类

**openfun/ralph** 📊
- 学习数据分析 LRS 工具包
- xAPI 语句存储
- Docker + Elasticsearch 部署
- MIT license
- https://github.com/openfun/ralph

### 3. Asset Management 类

**allegro/ralph** 🗄️
- DCIM + CMDB 数据中心管理
- Apache v2.0
- https://github.com/allegro/ralph

---

## Ralph Pattern 核心引用

> Geoffrey Huntley's Ralph pattern: https://ghuntley.com/ralph/

核心理念：
1. 上下文可以随时清空（LLM 上下文有限）
2. 重要信息全部写进文件（git/PRDs/日志）
3. 小任务（story）比大任务好
4. 迭代累积学习（progress.txt append-only）

---

## Ralph 与 Hermes 结合的价值

| Ralph 模式 | Hermes 对应 |
|-----------|-----------|
| prd.json | skill 任务清单 / memory |
| progress.txt learnings | dojo.py distill_findings_to_memory() |
| 文件即记忆 | memory palace / LCM 记忆系统 |
| 每次迭代清空 context | subagent 独立上下文 |
| AGENTS.md 更新 | CLAUDE.md / 记忆宫殿更新 |
| 迭代循环 + 退出信号 | Cron 触发 + 条件退出 |

Ralph 模式非常适合作为 Hermes 的**任务执行层**：
- 战略层：Hermes（记忆、规划、决策）
- 执行层：Ralph Loop（PRD 驱动、subagent 代执行）
