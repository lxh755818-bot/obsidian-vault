---
name: self-evolution-system
description: AI Agent 自我进化系统——错误追踪 + 知识输入 + 技能固化。核心循环：收到任务→执行→错误？→记录→复盘→固化技能。
version: 1.1.0
author: 小a
license: MIT
tags: [self-evolution, error-tracking, knowledge, skills]
hermes:
  cron_schedule: null
  created: 2026-04-25
  updated: 2026-04-25
---

# AI Agent 自我进化系统

## 核心理念

**犯错 → 记录 → 复盘 → 固化技能**

两条进化线：
- **被动进化**：犯错后记录、复盘、固化到技能（你提出的"改错"方向）
- **主动进化**：RSS输入 → 知识筛选 → 入库 → 指导下次任务（信息驱动方向）

## 核心循环

```
收到任务/需求
    ↓
理解层（记忆+上下文）→ 判断用什么技能
    ↓
执行层（技能+工具）→ 产出结果
    ↓
反馈层：错误？→ 记录 → 复盘 → 固化到技能
    ↓
存储层：知识入库 + 飞书日报
```

## 信息输入系统

### RSS 源（10个）

**AI/技术方向**
- Hugging Face Blog: huggingface.co/blog/rss.xml
- Arxiv CS.AI: arxiv.org/rss/cs.AI
- Arxiv CS.LG: arxiv.org/rss/cs.LG
- Simon Willison: simonwillison.net/atom.xml
- DeepMind Blog: deepmind.com/blog/feed/basic
- OpenAI Blog: openai.com/blog/rss.xml
- Lil'Log: lilianweng.github.io/atom.xml

**效率/技能方向**
- Gwern: gwern.net/news.xml

**产品/趋势方向**
- Product Hunt: producthunt.com/feed

### 内容分类标签
- `错误案例`：别人踩过的坑
- `技能优化`：工具调用、流程改进
- `Prompt改进`：提示词优化案例
- `工具情报`：新工具/框架/平台
- `趋势情报`：行业方向、大模型动态

## 知识库结构（Obsidian）

```
AI进化知识库/
├── 📥 每日输入/
│   ├── yyyy-mm-dd.md（每日汇总）
│   ├── 错误案例/
│   ├── 技能优化/
│   ├── Prompt改进/
│   └── 趋势情报/
├── 🛠️ 技能库/
│   ├── 已固化/（SKILL.md）
│   └── 待优化/
├── 🔄 进化日志/
│   ├── 错误记录/（每条错误一个文件）
│   └── 优化复盘/（复盘文档）
└── 📊 周报/月报/
```

## 飞书日报格式

```
📅 AI进化日报 - 4月25日

【今日输入】
• GitHub Trending: x个Repo入选
• RSS: x篇精选

【进化素材】
• 错误案例: N条（摘要）
• 技能优化: N条
• Prompt改进: N条
• 趋势情报: N条

【技能状态】
• 技能总数: 35个
• 本周新增: 2个
• 待优化: 3个

【错误追踪】
• 总记录: 12条
• 已复盘: 10条
• 待复盘: 2条
```

## 组件能力对照

| 组件 | 能力 |
|------|------|
| 定时调度 | Hermes cron ✅ |
| RSS解析 | feedparser + urllib ✅ |
| GitHub Trending | requests ✅ |
| 内容筛选 | LLM 判断质量+分类 |
| Obsidian存储 | obsidian skill ✅ |
| 飞书推送 | feishu skill ✅ |
| 错误记录 | 待开发 |
| 技能固化 | skill-cycle-optimizer 机制可复用 |

## 与现有系统关系

- **skill-cycle-optimizer**：每2小时测试一个技能，评估性能变化 → 整合进进化系统
- **log-error-correction**：每12小时检查错误日志 → 进化系统的错误输入源
- **选股系统**：独立核心业务，和进化系统并列

## 设计原则

1. **错误优先**：每次错误都要记录，复盘后固化到技能
2. **渐进式**：先跑通 GitHub Trending + RSS，微信/Twitter 等方案解决再加
3. **两条腿走路**：被动进化（改错）+ 主动进化（信息输入）缺一不可
4. **可验证**：日报量化进化进度，技能数↑、错误数↓

## 四环控制架构（已落地实现）

Ralph Loop 是本系统"反馈层"的完整工程实现，基于三项研究（见 `references/ralph-loop-control-theory.md`）：

- `references/ralph-loop-control-theory.md` — 四环控制架构理论来源
- `references/minimax-cn-api-key-debugging.md` — 2026-04-30 MiniMax CN API key 调试完整记录

```
JUDGE → ACTOR → JUROR → TERMINATOR
```

- **JUDGE**：读 PRD → 选 story → dispatch
- **ACTOR**：delegate_task subagent 执行故事
- **JUROR**：评审 + EXPLORE/EXPLOIT/REDESIGN 策略切换
- **TERMINATOR**：量化终止判断（5% 收敛阈值 + 最小迭代保护）

**关键实现文件**：`~/.hermes/scripts/ralph_*.py` + `~/.hermes/skills/mlops/hermes-ralph-loop/SKILL.md`

**Ralph Loop v2（2026-04-30）重大升级**：
- 裸 Anthropic API → `hermes chat -q @file -t terminal`，sub-agent 获得真实 terminal+file 工具
- 完整 session 持久化管理（超时前持久化 + resume 恢复）
- Auto-continue：`max-turns=30` 耗尽后自动 resume 最多 3 次
- Commit 格式硬性约束（解决 `US-US-996` 重复前缀问题）
- 完整实现细节见 `hermes-ralph-loop` skill 的 `references/ralph-iteration-v2-impl.md`

---

## Ralph 每日 Cron
> Ralph = 系统的自动优化引擎，主动从系统状态中发现问题、生成故事、闭环修复。

### 核心设计（2026-04-30 确立）

**旧范式**：Ralph 被动执行用户给定的 PRD → story 来自外部输入
**新范式**：Ralph 主动扫描系统状态 → 从异常中生成 story → 自动迭代修复

```
每日 Cron 触发
    ↓
Ralph 扫描 anomaly 来源：
  - log-error-correction 输出（未关闭错误）
  - skill-cycle-optimizer 输出（失败技能）
  - Clawvard 错题（Retrieval/Reasoning/Execution 分类）
  - 选股系统每日结果
    ↓
选最高优先级的一个
    ↓
Ralph 迭代处理（reasoning + 改进方案）
    ↓
distill_learnings → vault push
    ↓
飞书通知
```

### 适用条件

Ralph 适合处理**知识/记忆类问题**（今天"忘记 MiniMax 图片理解 key"就是这个类型）：
- 错误根因分析（为什么忘记/为什么出错）
- 记忆系统改进（怎么固化避免再犯）
- 流程优化（怎么让系统自己发现问题）

代码执行类问题 → 直接修复即可，不需要走 Ralph 循环。

### Ralph 处理类型对照

| 类型 | 来源 | Ralph 适合？ |
|------|------|-------------|
| 忘记某件事 | 用户反馈/自己发现 | ✅ 生成 story 分析根因 |
| 工具调用失败 | skill-cycle-optimizer | ✅ 分析失败原因 |
| 推理错误 | Clawvard 错题 | ✅ 分类错误类型 |
| 选股结果异常 | 每日选股报告 | ✅ 技术分析改进 |
| 代码 bug | 错误日志 | ❌ 直接修，不需要走循环 |

### Case Study（2026-04-30）— US-996 完整执行记录

**事件**：忘记 MiniMax 图片理解 CN API key 的逻辑。

**处理过程**：
1. 用户发截图 → 小a 尝试 MCP 工具 → login fail
2. 小a 用 execute_code + 直接 API → 成功（用 session 历史残片 key）
3. 发现 execute_code 读 .env 能拿到真实值，terminal 读是 `***`（sandbox 文件视图不同步）
4. Ralph 触发 US-996 → 9轮迭代，JUROR 返回 REDESIGN
5. Ralph 发现：`.env` 存储层就脱敏（不是显示问题）+ session compaction 截断 key
6. 小a接手完成：独立 secrets 文件 + 脚本 + skill更新 + learnings写vault + push + 飞书通知

**Ralph 执行发现的关键事实**：
- `.env` 和 `auth.json` 在**存储层**就脱敏，不是只在前端显示
- session compaction 把 `sk-cp-iS82xxxxxx` 压缩成 `sk-cp-...4IWg`
- MCP tool 确认 broken，绕过 MCP 才能 work
- learnings/ 目录存在但是空的，Ralph 需要创建文件

**关键教训**：
- key 信息只记在 session 历史里 → 不可靠（compaction 截断 + .env 脱敏）
- key 应固化到：① mem9 ② skill 文档 references/ ③ vault learnings
- Ralph 能自主分析根因并产出部分成果（即使 story 没完全 close）

### Ralph 迭代终止后的正确处理流程

当 Ralph 返回 **REDESIGN** 或耗尽迭代仍未 close story 时，正确流程：

```
Ralph 迭代终止（REDESIGN / max-iterations）
    ↓
Ralph 产出部分成果（learnings 写 vault，progress.txt 记录发现）
    ↓
检查 Ralph 发现的阻塞点类型：

  【A】需要用户提供信息（真实 key / 外部凭证 / 决策确认）
      → 小a 直接接手，用 Ralph 的分析结论继续执行
      → 完成后按完结流程处理（commit → distill → push → prd → 飞书）
      → 不重新触发 Ralph，因为分析工作已完成

  【B】Ralph 能力范围外的技术问题（npm 依赖冲突 / 网络不通 / 环境缺失）
      → 小a 评估：能修则修，修复后完结流程
      → 不能修则标记阻塞，明确告知用户需要什么

  【C】Ralph 分析方向完全错误
      → 重新写 PRD，调整 acceptance criteria
      → 重新触发 Ralph

关键原则：Ralph 产生的分析成果（progress.txt / learnings / 根因发现）
         不因为 story 没 close 就丢弃
         这些是进化系统的核心输入
```

**US-996 正确流程示意图**：
```
Ralph 9轮迭代 → 发现 .env 存储层脱敏（关键根因）
    ↓
阻塞点 = 需要用户提供真实 key（类型A）
    ↓
小a 接手 → 用 secrets/ 独立文件方案完成
    ↓
US-996 closes
```

---

### Ralph 迭代完结标准流程（6步）

当 Ralph 产出结果后（小a或刘大虾接手），按以下顺序完结迭代：

```
1. 若有代码/配置改动 → commit 到正确仓库（hermes 或 vault）
2. distill_learnings() → learnings 写入 Obsidian vault
3. bash obsidian_vault_sync.sh → push 到 GitHub
4. 更新 prd.json → passes: true
5. hermes-feishu 通知 → 发飞书给用户（oc_xxx）
6. 若 vault push 超时 → 标记状态，下次同步补推
```

**为什么这个流程重要（US-996 教训）**：
- learnings 没 push → 价值归零，下次迭代看不到
- 没通知用户 → 用户不知道系统已优化
- 没更新 prd.json → Ralph 下次跑同一个 story

**vault push 超时处理**：
- git pull --rebase 后再 push（解决 diverged branch）
- 超时不影响迭代状态，异步等待即可
- 不要让 vault push 阻塞主流程

---

## 状态

- [x] 四环控制架构已落地（feedback 层的工程实现）
- [x] Ralph 每日 Cron 设计（2026-04-30 确立新范式）
- [ ] Ralph Cron 具体 cron 表达式配置（待定）
- [ ] anomaly 来源接入（log-error-correction / skill-cycle-optimizer）
- [ ] 与 hermes-dojo 整合（统一 Monitor+Analyzer → JUROR，Fixer → ACTOR）
- [ ] GitHub Trending + RSS 先行
- [ ] 技能固化流程整合
