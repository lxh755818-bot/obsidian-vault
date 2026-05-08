# Source: `hierarchical-memory-tree`

---
name: hierarchical-memory-tree
category: mlops
description: 分层记忆树架构 — AI Agent 记忆系统从单文件 append 到分层指针架构的演进设计，包含容量控制、CRON 摘要流程和层级淘汰策略
tags: [memory, architecture, agent, sqlite, crontab]
---

# 分层记忆树 (Hierarchical Memory Tree)

## 问题背景

单文件 append 模式的记忆系统（如单一大 MEMORY.md）在长期运行后必然膨胀到不可维护。需要分层指针架构实现自动淘汰和按需回溯。

## 架构设计

```
MEMORY.md (L0 根索引, 目标 < 5KB)
    │
    └── memories/
        ├── skills/
        │   ├── skill-a.md
        │   └── skill-b.md
        ├── user/
        │   └── profile.md
        ├── projects/
        │   └── project-x.md
        └── topics/
            ├── topic-a.md
            └── topic-b.md
```

### 层级职责

| 层级 | 文件 | 保留内容 | 淘汰策略 |
|---|---|---|---|
| L0 根 | `MEMORY.md` | 高层摘要、指针索引、核心事实 | 只保留最精华的，硬上限 5KB |
| L1 域 | `memories/*/` | 按领域聚合 | 超容量时拆分成 L2 |
| L2 详 | `memories/*/*.md` | 具体记录、完整会话摘要 | 超过 20KB 时拆分到历史目录 |

### 容量控制规则

```
MEMORY.md      ─── 目标 < 5KB,  硬上限
memories/*/    ─── 单文件目标 < 50KB
memories/*/*.md ── 超 20KB 自动拆分
```

## CRON 摘要任务流程

```
触发条件 (满足任一):
  • 超过 50 条新会话消息
  • 超过 2 小时无活动
  • 每天凌晨自动执行

Step 1: 提取关键信息 (从 SQLite)
  • 新学到的用户事实/偏好
  • 解决的技术问题 + 方案
  • 做出的重要决策
  • 未完成的后续任务

Step 2: 判断写入层级
  • 核心事实 → MEMORY.md
  • 领域相关 → memories/[domain]/
  • 详细记录 → memories/*/*.md

Step 3: 写入 + 触发容量检查
  • 如果 MEMORY.md 超 5KB → 压缩/下移
  • 如果子文件超限 → 拆分成多个文件
  • 更新指针索引

Step 4: 输出摘要报告
  • 本次新增了哪些记忆
  • 触发了哪些整理动作
  • 整体记忆系统健康状态
```

## 查询路径

```
用户问: "上次部署服务的事还记得吗？"
     │
     ▼
1. 查 MEMORY.md 索引 → 发现 memories/projects/cloud-deploy.md
2. 读 memories/projects/cloud-deploy.md → 找到摘要
3. 如需细节 → 读 memories/projects/cloud-deploy/sessions/session-17.md
```

## 行业系统对比 (2026-04-22 调研更新)

| 系统 | Stars | 架构 | 检索 | 自进化 | Hermes 现状 |
|---|---|---|---|---|---|
| Mem0 | ~15k | 向量+混合搜索+LLM压缩 | 语义+BM25+实体 | ✅ v3 自研 | 差：无 embedding |
| agentmemory | 1.8k | 4-tier压缩+知识图谱 | BM25+向量+图谱 | ❌ | 差：无自动压缩 |
| jzOcb | ~200 | L0/L1/L2+P0/P1/P2+TTL | 文件搜索 | 部分 | 接近，有差距 |
| HMLR | 377 | 多跳推理+Fact Store | 向量+SQL事实 | ❌ | 差：无推理增强 |
| AIAnytime | 35 | 9策略对比框架 | RAG+重要性评分 | ❌ | 参考价值 |
| Hermes (当前) | — | L0/L1/L2/L3+BM25 | BM25+TF-IDF | ✅ 技能自进化 | — |

**关键差距**：无自动 TTL 清理（jzOcb 的 memory-janitor.py）、无 Q1/Q2/Q3 写入规范、无隐私过滤。

## Q1/Q2/Q3 写入决策框架（jzOcb 融合）

每次写入记忆前必须过判断流程：

```
Q1: 下次醒来不看这条，会做错事吗？
  → Yes: 写入 MEMORY.md [P0]（永不过期）
  → No:  继续Q2

Q2: 某天可能需要查这条吗？
  → Yes: 写入 archive/ [P1]（90天后清理）
  → No:  留在 daily log，不处理

Q3: 以上都不是？
  → 留在 daily log，不沉淀
```

### 对应 Priority 标签

| 判断 | Priority | TTL | 位置 |
|------|----------|-----|------|
| Q1=Yes | `[P0]` | 永不过期 | MEMORY.md |
| Q2=Yes | `[P1][YYYY-MM-DD]` | 90天 | archive/ |
| Q3=No | `[P2][YYYY-MM-DD]` | 30天 | archive/ |
| 纯日志 | — | — | daily/ |

### 硬性限制

```
MEMORY.md ≤ 150 行 — 硬约束，超过必须精简
L3 semantic.db 单条 ≤ 500 tokens
```

## P0/P1/P2 + TTL 自动清理（memory-janitor.py）

**目标**：解决记忆无限堆积、无自动过期清理的核心缺陷。

```python
# ~/.hermes/scripts/memory_janitor.py
# 每日 Cron 触发，检查以下内容：

# 1. MEMORY.md 行数检查
#    if len(lines) > 150: 警告并输出需精简的条目

# 2. P1/P2 条目 TTL 检查
#    P1 → 90天未访问 → 移入 archive/
#    P2 → 30天未访问 → 移入 archive/

# 3. daily/ 日志检查
#    超7天的日志 → 可选压缩或保留

# 4. L3 semantic.db 访问频率更新
#    每次命中 +1 access_count
#    30天未命中 -1（Ebbinghaus 遗忘曲线）
#    access_count < -3 → 标记为低价值，可删除
```

### 隐私过滤（写入前必执行）

所有写入记忆的内容必须通过隐私过滤，防止 API key/token 泄露：

```python
import re

PRIVACY_PATTERNS = [
    (r'MINIMAX[_-]API[_-]KEY\s*=\s*["\']?[^"\'\s]+', 'MINIMAX_API_KEY=***'),
    (r'API[_-]KEY\s*=\s*["\']?sk-[^"\'\s]+', 'API_KEY=***'),
    (r'ghp_[a-zA-Z0-9]{36}', 'ghp_***'),
    (r'xox[baprs]-[a-zA-Z0-9]{10,}', 'xoxb_***'),
    (r'bearer [a-zA-Z0-9_\-\.]+', 'bearer ***', re.IGNORECASE),
    (r'token["\']?\s*:\s*["\']?[a-zA-Z0-9_\-\.]+', 'token: ***'),
]

def privacy_filter(text: str) -> str:
    for pattern, replacement in PRIVACY_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text
```

## 4-Tier 记忆压缩（agentmemory 融合）

| 层 | 内容 | 淘汰策略 |
|---|---|---|
| **Working** | 原始观察（工具调用结果、对话） | 5min窗口去重后转 Episodic |
| **Episodic** | 单会话压缩摘要 | 30天未访问转 Semantic |
| **Semantic** | 提取的事实和模式 | 90天未访问转 archive |
| **Procedural** | 工作流和决策模式 | 永久保留，定期更新 |

**Ebbinghaus 遗忘曲线应用**：
- 每次访问记忆 → `access_count += 1`
- 每7天未访问 → `access_count -= 1`
- `access_count < -3` → 移出 L3，保留在 archive
- 高频访问（>5次）→ 自动标记为 P0 候选

## RunawayContext 四层架构（v3 最终形态）

> 2026-04-22 调研 GitHub 多个记忆系统后融合确定：RunawayContext（架构层）+ cass（规则学习层）

```
kk_repo (git@github.com:lxh755818-bot/kk.git)
├── CONSTITUTION.md          ← T1 系统宪法
│   身份定义 + 行为准则 + 知识路由 + 协作分工
├── LIVING_MEMORY.md          ← T2 行为纠正
│   Cass 规则学习 + 置信度衰减教训 + 每日蒸馏
├── AGENT_COMM.md             ← T3 协作记录（小a ↔ 刘大虾）
│   Bot-to-Bot 通信日志 + 协作决策
├── projects/                 ← T3 项目 Brain（各子目录）
│   ├── stock-selector/BRAIN.md    ← 选股系统
│   ├── feishu-integration/BRAIN.md ← 飞书集成
│   └── memory-system/BRAIN.md      ← 记忆系统
├── KNOWLEDGE_STORE.md         ← T4 知识库索引
│   飞书多维表格结构 + 工具副表 + 共享知识库
└── README.md                  ← 四层串联说明
```

### T1: CONSTITUTION.md（系统宪法）
- **用途**：定义 Agent 身份、行为准则、知识路由规则、与刘大虾的协作分工
- **路由规则**：`skill → memory → session_search → kk_repo`
- **更新频率**：仅重大决策时更新
- **容量**：硬上限 200 行

### T2: LIVING_MEMORY.md（行为纠正）
- **用途**：Cass 规则学习的教训记录（每次错误/纠正后写入）
- **格式**：`<错误描述> → <教训> → <正确行为>`
- **容量**：≤50 行，超过则蒸馏到 archive

### T3: projects/*/BRAIN.md（项目 Brain）
- **用途**：各项目的子记忆，包含状态/TODO/坑点/技术栈
- **当前项目**：选股系统、飞书集成、记忆系统
- **更新频率**：每次项目状态变化时更新

### T4: KNOWLEDGE_STORE.md + 飞书多维表格
- **本地索引**：`KNOWLEDGE_STORE.md` — 飞书 7 个副表的字段/用途/记录数索引
- **飞书工具副表**（`tbly7MjpPbPLkasd`）：12 个已注册工具的能力清单
- **Base Token**：`PlsLbTLynaIF3qsoVXCctXTcnnf`

### 与刘大虾的协作分工
| 维度 | 小a (Android/Termux) | 刘大虾 (PC/OpenClaw) |
|------|---------------------|---------------------|
| 平台 | 移动端，快速采集 | PC 端，深度分析 |
| 记忆 | semantic.db (9条活跃) | MemPalace (39k抽屉) |
| 检索 | FTS5 关键词 | ChromaDB 语义 |
| 共享 | kk_repo + 飞书 Bitable | kk_repo + 飞书 Bitable |

## 实际实现状态 (2026-04-22 更新 v3)

| 组件 | 状态 | 路径/说明 |
|---|---|---|
| L0 MEMORY.md 索引 | ✅ 已创建 | `~/.hermes/MEMORY.md`（35行/1629字节） |
| L1 每日日记 | ✅ 已创建 | `~/.hermes/memory/daily/YYYY-MM-DD.md` |
| L2 领域分域存储 | ✅ 已建立 | `~/.hermes/memory/{skills,user,projects,topics,archive}/` |
| L3 语义搜索（升级版） | ✅ 已实现 | `~/.hermes/scripts/memory_l3.py`（BM25+TF-IDF，P0/P1/P2标签，隐私过滤） |
| RunawayContext 四层架构 | ✅ 已建立 | `kk_repo/` T1-T4，GitHub 共享 |
| kk_repo T1 CONSTITUTION.md | ✅ | 身份/行为准则/路由/协作分工 |
| kk_repo T2 LIVING_MEMORY.md | ✅ | Cass规则教训/每日蒸馏教训 |
| kk_repo T3 projects/BRAIN.md | ✅ | 选股/飞书/记忆系统 3个项目brain |
| kk_repo T4 KNOWLEDGE_STORE.md | ✅ | 飞书7个副表索引 |
| 飞书工具副表 12 条注册 | ✅ | `tbly7MjpPbPLkasd`，active |
| Cass 置信度衰减脚本 | ✅ 已实现 | `~/.hermes/scripts/memory_decay.py` |
| memory-decay Cron（22:00） | ✅ 已注册 | `job_id: 021cac06ed16` |
| Janitor Cron（03:00） | ✅ 存在 | `job_id: b92a71a42a9f`（旧版，保留） |
| Q1/Q2/Q3 写入规范 | ✅ 已记录 | 见上方框架，待实施到 prompt |
| 隐私过滤 | ✅ 已集成 | memory_l3.py 内置 |
| L3 access_count 追踪 | ✅ 已实现 | mark_hit() 在 search 时自动调用 |
| Ebbinghaus 遗忘加权 | ✅ 已实现 | 30天未访问 → access_count -= 1 |
| L3 → archive 自动归档 | ✅ 已实现 | P1 90天/P2 30天超期 → 移入 archive/ |
| Q1/Q2 写入 prompt 集成 | ❌ 缺失 | 仍在框架阶段 |

**已实施：memory-janitor.py（TTL清理）+ L3 access_count追踪

**下一步优先级**：

## Cass 置信度衰减（memory_decay.py）

cass 的核心机制是"规则学习 + 置信度衰减"。在 Termux 上无法安装 cass 二进制，但可用纯 Python 实现相同逻辑。

```bash
# 手动运行
python3 ~/.hermes/scripts/memory_decay.py

# 输出示例（正常无动作时）
# [id= 1] P0 acc=1  0d conf=0.200 | 保持 | 刘小豪是我的主人...
# [2026-04-22 22:00] 完成 | 活跃 9 | 已归档 0 | 本次动作 0
```

**衰减规则**：
| 条件 | 动作 |
|------|------|
| P0 + 14天未访问 | P0 → P1 |
| P1 + 30天未访问 | P1 → P2 |
| P2 + 60天未访问 | 移入 `memories_archive` 表 |
| 新记忆 access_count=0 + 3天 | 首次激活（0→1） |

**Cron**：`021cac06ed16` 每日 22:00 执行

## RunawayContext 四层架构使用

```bash
# T1 宪法（只读，重大决策时更新）
cat ~/.hermes/kk_repo/CONSTITUTION.md

# T2 行为纠正（每次犯错后追加）
cat ~/.hermes/kk_repo/LIVING_MEMORY.md

# T3 项目状态
cat ~/.hermes/kk_repo/projects/stock-selector/BRAIN.md
cat ~/.hermes/kk_repo/projects/feishu-integration/BRAIN.md

# T4 知识库
cat ~/.hermes/kk_repo/KNOWLEDGE_STORE.md

# GitHub 同步（小a ↔ 刘大虾）
cd ~/.hermes/kk_repo && git pull && git push
```

## L3 语义搜索使用方式

```bash
# 添加记忆（自动隐私过滤 + P0/P1/P2 标签）
python3 ~/.hermes/scripts/memory_l3.py add "记忆内容" "category" [P0|P1|P2]

# 搜索记忆（自动 access_count +1）
python3 ~/.hermes/scripts/memory_l3.py search "查询内容" [top_k]

# 查看统计
python3 ~/.hermes/scripts/memory_l3.py stats

# 列出所有记忆
python3 ~/.hermes/scripts/memory_l3.py list

# 设置优先级
python3 ~/.hermes/scripts/memory_l3.py set-priority <id> P0

# 删除记忆
python3 ~/.hermes/scripts/memory_l3.py delete <id>
```

**技术方案**：BM25 + TF-IDF 混合搜索（纯本地，不依赖外部付费 API）。中英文分词支持，中文二元组覆盖。

## 刘大虾系统对比（参考基准，2026-04-22 更新）

| 层级 | 刘大虾 | 小a（当前） | 差距 |
|---|---|---|---|
| T1 宪法 | 无 | ✅ kk_repo/CONSTITUTION.md | 小a 领先 |
| T2 行为纠正 | 无 | ✅ kk_repo/LIVING_MEMORY.md | 小a 领先 |
| T3 项目 Brain | 无 | ✅ kk_repo/projects/ | 小a 领先 |
| T4 知识库 | 飞书（手动） | ✅ 飞书+Knowledg_STORE.md | 小a 领先 |
| L1 日记 | `daily/*.md` 无限制 | ✅ `memory/daily/` | 量级接近 |
| L2 索引 | 195行/50KB | ✅ MEMORY.md | 接近 |
| L3 语义 | MemPalace（39k抽屉） | ✅ BM25+TF-IDF（9条） | 功能可用，容量差 |
| 置信度衰减 | Mem0 内置 | ✅ memory_decay.py | 刘大虾 领先 |
| 协作共享 | 各自独立 | ✅ kk_repo GitHub | 小a 领先（Bot-to-Bot） |
| 蒸馏自动化 | 每日 22:00 | ⚠️ memory-decay Cron（22:00），但仅衰减无蒸馏 | 待加强 |

**下一步优先级**：

| 方向 | 成本 | 收益 | 状态 |
|---|---|---|---|
| **Q1/Q2/Q3 写入 prompt 集成** | ⭐ | 提升记忆质量，减少垃圾 | 🥇 待实施 |
| **每日蒸馏 Cron（sessions → daily）** | ⭐⭐ | 自动沉淀，不用手动整理 | 🥈 待实施 |
| **Layer 3 向量语义检索** | ⭐⭐ | 语义匹配能力提升 | ❌ Termux 不支持 |

**已解决的历史问题**：
- ❌ ChromaDB 本地 → 放弃（依赖 torch，无法安装）
- ❌ sqlite-vss → 放弃（lancedb 包名冲突）
- ❌ cass 二进制 → 放弃（glibc 不兼容），改用 Python 模拟
- ✅ BM25 本地搜索 → 已实现，8条记忆可用
- ✅ RunawayContext 四层架构 → 已落地 kk_repo
- ✅ Cass 置信度衰减 → 已用 Python 实现

## 失败教训（真实踩坑记录）

### 1. Mem0 安装失败
- **尝试**：`pip install mem0ai`
- **错误**：grpcio 从源码编译超时（Android Termux 交叉编译 C++ grpc 库极慢）
- **处理**：kill 后台进程，放弃
- **结论**：任何依赖 grpcio、torch 等从源码编译的包，在 Termux 上都极难安装

### 2. MiniMax Embedding API 余额不足
- **尝试**：直接调用 `api.minimaxi.com/v1/embeddings`
- **错误**：`status_code: 1008, status_msg: "insufficient balance"`
- **处理**：改用 BM25 本地搜索
- **结论**：embedding API 需要付费，免费额度容易耗尽，提前验证

### 3. 直接 API vs MCP 工具
- **MCP 工具** `mcp_minimax_understand_image`：持续 login fail
- **直接 API** `/v1/coding_plan/vlm`：成功
- **教训**：MCP 封装可能有 bug 或认证问题，直连 API 更可靠

### 4. cass 源码构建失败（glibc 不兼容）
- **尝试**：`cargo build --release` 从源码构建 `coding_agent_session_search`
- **问题**：cass 二进制依赖 glibc `/lib/ld-linux-aarch64.so.1`，Termux 使用 Bionic libc（Android）
- **分析**：cass v0.3.4 有 ARM64 构建，但所有平台二进制都链接 glibc 而非 Bionic
- **源码 path dependencies**：`Cargo.toml` 引用 `/data/projects/frankensearch` 等 5 个 sibling crates，完整构建需要同时克隆多个仓库
- **处理**：放弃二进制，转而用 Python 模拟 cass 的置信度衰减逻辑
- **结论**：cass 的核心理念（规则+置信度+衰减）在 semantic.db 中用纯 Python 即可实现

### 5. Omni-SimpleMem 安装失败（lancedb 依赖冲突）
- **尝试**：`pip install lancedb` / `pip install simplemem`
- **问题**：`lancedb` 包名与 `pylance` 冲突；`simplemem` 依赖 `cachetools` 但 `pylance` 包也提供 `cachetools`，导入冲突
- **处理**：删除尝试的包，改用融合方案
- **结论**：Termux + Python 3.13 + Android aarch64 组合太新，第三方向量库基本无法 pip 安装

### 6. 飞书 Bitable 单选字段格式错误
- **错误**：`SingleSelectFieldConvFail`
- **原因**：传了 `{"text": "active"}` 对象格式，单选字段应直接传字符串 `"active"`
- **教训**：飞书 Bitable API 单选/多选字段直接传字符串，无需 `{"text": ...}` 包装

## BM25 实操指南（当前 L3 方案）

```bash
# 添加记忆
python3 ~/.hermes/scripts/memory_l3.py add "记忆内容" "category"

# 搜索
python3 ~/.hermes/scripts/memory_l3.py search "查询内容"

# 统计
python3 ~/.hermes/scripts/memory_l3.py stats
```

**依赖**：`pip install rank-bm25`（已验证在 Termux 上可装，0.05s）
**中文支持**：jieba 分词，二元组覆盖
**存储**：本地 SQLite `~/.hermes/memory/semantic.db`，不依赖外网

## 相关工具

- SQLite FTS5: 现有会话历史存储 (`~/.hermes/state.db`)
- CRON: 定时触发 (`~/.hermes/scripts/summarize_session.py`)
- mem0: 行业方案参考 (向量+关系混合)
- Qdrant Cloud: 云向量搜索备选 (REST API，安卓可用)

