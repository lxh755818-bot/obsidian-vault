# Source: `holographic-phase2-engineering`

---
name: holographic-phase2-engineering
category: mlops
description: Hermes Holographic Phase 2 工程化闭环 — 结构化元数据/BM25语义搜索/质量指标/自动归档/健康检查/召回命中率追踪
---

# Holographic Phase 2 工程化闭环

## 架构原则

```
记忆系统职责 = 认知连续性（跨会话、跨任务的记忆能力）
              ≠ 网关稳定性（那是独立层的问题）

LCM 压缩      → 压缩对话历史 DAG，不触及 fact_store
fact_store    → 独立于 LCM，LCM 压缩不触及 facts 表
这两层正交，不会因压缩丢失记忆深度
```

## 已实现的 6 项改进

### 1. FIX-QM — quality_metrics 表从 gateway 视角改为记忆视角

**旧指标（gateway 视角，移除）：**
- `over_budget_ratio`
- `avg_injected_chars`

**新指标（记忆视角）：**
- `avg_trust_score`
- `orphan_entity_ratio`（无 entity 链接的事实比例）
- `low_value_ratio`（trust<0.4 且 retrieval_count≤1 的事实比例）
- `vector_coverage`（有 HRR 向量的事实比例）
- `avg_recency_score`

### 2. FIX-INJECT — 移除 gateway 视角的注入预算参数

从 `FactStoreConfig` 移除：`max_injected_items` / `max_memory_chars_per_item` / `max_injected_chars_total`。这三个参数属于网关稳定性层，不属于记忆系统。

### 3. L7-BM25 — 三层语义召回

```python
WEIGHT_BM25 = 0.34   # 词汇语义（BM25）
WEIGHT_FTS5 = 0.18   # 精确关键词（FTS5）
WEIGHT_HRR  = 0.48   # 结构绑定推理（HRR）

# 字符级中文分词，无需 jieba
class ChineseCharacterTokenizer:
    def __tokenize(self, text: str) -> list[str]:
        import re
        return re.findall(r'[\u4e00-9fff]+|[a-zA-Z0-9]+', text)
```

### 4. ARCHIVE — 自动归档低价值事实

```python
# 归档条件（同时满足）
- 30天未触达（retrieval_count=0 或距今>30天）
- trust < 0.4
- retrieval_count ≤ 1
mem.archive_facts(threshold_days=30, max_trust=0.4, max_retrieval_count=1)
```

### 5. FIX-HC — health_check 记忆视角信号

- `high_orphan_ratio`（orphan_entity_ratio > 0.5）
- `low_recall_utilization`（avg_recall_hit_rate < 0.3）
- `low_trust_prevalence`（low_value_ratio > 0.4）
- `vector_coverage_low`（vector_coverage < 0.5）

### 6. HITRATE — 召回命中率追踪

```python
retriever.record_hit(fact_id)   # 召回时记录
hit_rate = retriever.get_hit_rate()  # 查询命中率
```

## 验证命令

```bash
cd ~/.hermes/hermes-memory/holographic
python3 - <<'EOF'
from src.fact_store import FactStore
fs = FactStore(".holographic/fact_store.db")
print(fs.get_quality_report())
print(fs.health_check())
EOF
```

## 可选未完成项

- **L7 sentence-transformers**：pip install 后接 Faiss 混合索引
- **mem9**：跨 Agent 记忆共享（Hermes ↔ OpenClaw），api.mem9.ai，官方插件。额外价值在跨 Agent 共享，不在 fact 提取（已有 extract 能力）
