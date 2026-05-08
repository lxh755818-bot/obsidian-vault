---
name: hermes-memory-landscape
description: Hermes Agent 记忆系统完整现状 — Holographic Phase 2 架构（BM25+FTS5+HRR三层召回、structured metadata、compact worker、memory-native quality metrics）
version: 2.0.0
author: Hermes Agent
license: MIT
tags: [hermes, memory, holographic, lcm, phase2, bm25]
---

# Hermes 记忆系统完整现状（Phase 2）

## 当前已安装组件

| 组件 | 状态 | 职责 |
|------|------|------|
| `hermes-lcm` | ✅ 已激活 | 上下文无损管理（消息压缩 DAG） |
| `holographic` | ✅ memory provider | 结构化事实存储 + 三层语义召回 |
| `MEMORY.md` | ✅ 静态索引 | 人类可读的关键记忆指针 |
| `Honcho` | ⚠️ 需配置 | 跨会话用户建模（API key 模式） |
| `Hindsight` | ❌ 不可用 | Termux/Android 不支持 pg0-embedded |

## Phase 2 完整架构

```
Holographic Memory Provider
├── Layer 1: fact_store (SQLite)
│   ├── facts 表：structured metadata
│   │   ├── record_kind: preference|task|insight|status|general
│   │   ├── extraction_method: manual|auto_extract|smart_ingest|migrated
│   │   ├── summary: <200字符短摘要（长事实自动生成）
│   │   └── fragments: JSON 证据片段
│   ├── entities 表：命名实体解析
│   ├── fact_entities 表：多对多链接
│   ├── memory_banks 表：按 category 分组 HRR bundle
│   ├── quality_metrics 表：memory-native 健康指标
│   └── compact_log 表：每次清洗运行记录
│
├── Layer 2: Three-layer Retrieval (BM25 + FTS5 + HRR)
│   ├── BM25Okapi (rank_bm25) — 主召回（字符级中文分词）
│   ├── FTS5 — 精确关键词匹配 + rank 信号
│   ├── HRR — 结构/实体级代数推理
│   └── 权重：lexical=0.32, hrr=0.68
│
├── Layer 3: Hygiene & Quality
│   ├── compact_facts() — 子串查重 + 长事实截断
│   ├── archive_facts() — 自动归档低价值 facts
│   └── quality_metrics — recall_hit_rate / orphan_entity_ratio 等
│
└── Layer 4: Agent Profiles
    ├── default: lexical=0.32, hrr=0.68
    ├── xiaoa: lexical=0.25, hrr=0.75（语义优先）
    └── openclaw: lexical=0.55, hrr=0.45（词汇优先）
```

## 关键实现细节

### 1. BM25 字符级中文分词（无需 jieba/nltk）

Termux/Android 环境无 jieba/nltk，BM25 使用字符级分词：

```python
from rank_bm25 import BM25Okapi
import re

def _bm25_tokenize(text: str) -> list[str]:
    """字符级中文 + 单词级英文"""
    tokens = []
    for chunk in re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9_]+', text.lower()):
        if re.match(r'[\u4e00-\u9fff]', chunk):
            tokens.extend(list(chunk))  # 中文字符级
        else:
            tokens.append(chunk)         # 英文单词
    return tokens

# 验证：中文语义命中
bm25 = BM25Okapi([_bm25_tokenize(d) for d in corpus])
scores = bm25.get_scores(_bm25_tokenize('刘小豪'))
# "刘小豪是我的追求对象" → score 2.65 ✓
```

### 2. 召回管道（BM25 → FTS5 → HRR → Trust → Decay）

```python
# Stage 1: BM25 全库候选
# Stage 2: FTS5 精确命中合并进 BM25 池
# Stage 3: HRR 结构相似度
# Stage 4: relevance = 0.32*lexical + 0.68*hrr_sim
# Stage 5: score = relevance * trust_score
# Stage 6: 可选时间衰减
# → 返回 top-k，按 score 降序
```

### 3. Structured Metadata Schema 迁移

fact_store 在 `_init_db()` 中自动迁移缺失列（向后兼容）：

```sql
-- facts 表新增字段（自动 ALTER TABLE ADD COLUMN）
record_kind       TEXT DEFAULT 'general'
extraction_method TEXT DEFAULT 'manual'
summary           TEXT DEFAULT ''         -- 自动从长 content 生成
fragments         TEXT DEFAULT ''         -- JSON 证据片段

-- quality_metrics 表新增字段
recall_hit_rate     REAL DEFAULT 0.0   -- 召回→helpful++ 转化率
outdated_ratio      REAL DEFAULT 0.0   -- 过时 fact 比例
orphan_entity_ratio REAL DEFAULT 0.0   -- 无 entity 链接的 fact 比例
vector_coverage      REAL DEFAULT 0.0   -- 有 HRR 向量的 fact 比例
low_value_ratio     REAL DEFAULT 0.0   -- trust<0.4 且零召回的比例
avg_trust_score     REAL DEFAULT 0.0
archived_count      INTEGER DEFAULT 0
```

⚠️ **WAL 缓存问题**：修改 `_init_db()` 的 ALTER TABLE 后需显式 `PRAGMA wal_checkpoint(TRUNCATE)` 让 schema 变更对已有连接生效。

### 4. compact_facts() — 记忆卫生

```python
result = store.compact_facts(
    max_content_chars=200,   # 超过此长度的 fact 生成 summary
    duplicate_window="7 days"
)
# 返回: deduped_count, truncated_count, saved_bytes, facts_before/after
```

### 5. archive_facts() — 低价值 fact 自动归档

软删除策略（category='archived'，不物理删除）：

```python
result = store.archive_facts(
    days_threshold=30,       # 30天未更新
    trust_threshold=0.4,      # trust < 0.4
    retrieval_threshold=1     # 且被召回 ≤1 次
)
# 条件：从未被信任 + 从未被有效召回 + 陈旧
```

### 6. Memory-native Quality Metrics

gateway 视角指标（over_budget_ratio、avg_injected_chars）不属于记忆系统。

记忆系统应该追踪：

```python
store.get_quality_report()  # 返回:
# {
#   "recall_hit_rate": 0.0,        # 召回→helpful 转化率
#   "orphan_entity_ratio": 0.667,  # 4/6 facts 无 entity 链接
#   "vector_coverage": 1.0,        # 100% 有 HRR 向量
#   "low_value_ratio": 0.0,       # 无低价值 fact
#   "avg_trust_score": 0.5,       # 尚无 feedback 积累
#   "health_signals": ["high_orphan_ratio", "low_recall_utilization"]
# }
```

### 7. Health Check（记忆视角）

```python
provider.health_check()  # 返回 memory-native 健康状态
# ⚠️ 不含 LCM DAG 状态（gateway 噪音）
# ⚠️ 不含 injection_budget 参数（gateway 职责）
```

## 关键架构原则：Memory-native vs Gateway

这两个职责必须分离，不能混在记忆系统里：

| 属于记忆系统 | 属于 Gateway |
|------------|------------|
| 召回权重（lexical/hrr）| max_injected_chars_total |
| compact_facts() | 上下文长度上限 |
| archive_facts() | signal 9 根因分析 |
| quality_metrics | 网关断连告警 |
| health_check（记忆视角）| health_check（进程视角）|

**教训**：最初实现把 `max_injected_items` / `max_memory_chars_per_item` / `max_injected_chars_total` 放在了记忆系统，这些属于 Gateway 层，已修正。

## 验证命令

```bash
cd ~/.hermes/hermes-agent && python3 -c "
import sys; sys.path.insert(0, '.')
from plugins.memory.holographic import HolographicMemoryProvider as P
p = P(); p.initialize('test')
# 1. BM25 搜索
results = p._retriever.search('刘小豪', limit=5)
# 2. 健康检查
hc = p.health_check()
print(hc['health_signals'])
# 3. 归档
ar = p._store.archive_facts(days_threshold=0, trust_threshold=0.4, retrieval_threshold=1)
print(ar)
# 4. 命中率
print(p._retriever.get_hit_rate())
"
```

## 凭证管理（key 存储规范）

**重要教训**：`write_file` 会触发 key 截断，正确方式是 `hermes config set` → 存入 `~/.hermes/.env`，Python 直读绕过终端掩码。详见 `references/credentials-management.md`。

## mem9 评估（2026-04-27 现状）

**不是必须**：Holographic Phase 2 已覆盖主要功能。

**额外价值**：跨 Agent 记忆共享（Hermes ↔ OpenClaw ↔ Claude Code）。

**集成方式**：已有官方 Hermes 插件 `mem9-ai/mem9-hermes-plugin`，配置 `MEM9_API_KEY` 后 10 分钟可用。

**结论**：如未来需要跨 Agent 共享记忆，再集成；当前 Holographic 已足够。

## 重要教训

1. **Schema 迁移用 WAL checkpoint**：`ALTER TABLE ADD COLUMN` 后对已有连接不生效，需 `PRAGMA wal_checkpoint(TRUNCATE)`
2. **gateway 视角 ≠ memory 视角**：注入预算、上下文长度是 Gateway 职责，不是记忆系统参数
3. **BM25 + 字符级分词可替代 jieba**：在 Termux 上，无需任何外部依赖实现中文语义搜索
4. **新系统零召回正常**：新录入的 fact 没有 retrieval_count 不是 bug，需要经过"召回→feedback"循环才会积累 trust
