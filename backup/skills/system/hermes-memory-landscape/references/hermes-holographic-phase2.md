# Source: `hermes-holographic-phase2`

---
name: hermes-holographic-phase2
description: |
  Phase 2 engineering upgrade for Hermes Holographic memory plugin (memory_store.db).
  Addresses signal 9 / OOM on gateway by adding: structured metadata schema, quality
  metrics, compact worker, injection budget enforcement, recall weight retuning
  (lexical 0.32 / HRR 0.68), per-agent profile weighting, and health check endpoint.
category: mlops
tags: [hermes, memory, holographic, hrr, sqlite, memory-management]
---

# Hermetic Holographic Phase 2 — Engineering Upgrade Guide

## Purpose
Systematic upgrade of the Hermes Holographic memory plugin to address memory bloat,
uncontrolled injection size, and weak recall quality. Signal 9 (SIGKILL) on the gateway
is typically OOM — not a gateway bug but a memory management problem.

## Architecture

```
memory_store.db (SQLite)
├── facts              — content + HRR vector + structured metadata
├── entities           — named entities extracted from fact content
├── fact_entities      — many-to-many links
├── memory_banks       — category-level HRR bundle vectors
├── quality_metrics    — time-series: duplicate_rate, noise_ratio, over_budget_ratio
└── compact_log        — history of storage cleanup runs

HolographicMemoryProvider
├── MemoryStore        — CRUD + compact + quality tracking
├── FactRetriever      — hybrid recall (FTS5 + HRR + trust + budget)
└── _AGENT_PROFILES    — per-agent weight overrides
```

## Phase 2 Layers (L1–L8)

### L1: Structured Metadata Schema
Add 4 columns to `facts` via `ALTER TABLE` (safe migration, existing DBs preserved):

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `record_kind` | TEXT | 'general' | preference \| task \| insight \| status \| general |
| `extraction_method` | TEXT | 'manual' | manual \| auto_extract \| smart_ingest \| migrated |
| `summary` | TEXT | '' | Short fact-card, auto-generated if content > 200 chars |
| `fragments` | TEXT | '' | JSON list of evidence snippets |

### L2: Quality Metrics Tracker
Two new tables:
- `quality_metrics` — duplicate_rate, noise_ratio, over_budget_ratio, avg_quality_score,
  active_count, indexed_count, avg_memory_chars, avg_injected_chars
- `compact_log` — facts_before/after, deduped_count, truncated_count, saved_bytes

API: `store.get_quality_report()`

### L3: Compact Worker
`store.compact_facts(max_content_chars=200)`:
1. Truncate facts > 200 chars with no summary → set summary = content[:197] + "…"
2. Near-duplicate detection via substring matching → delete shorter, keep longer
3. Log to compact_log

Schedule via cron every 6–12h or after large batch imports.

### L4: Recall Weight Retuning
| | Before | After |
|--|--------|-------|
| FTS/lexical | 0.4 | **0.32** |
| Jaccard | 0.3 | (absorbed into lexical) |
| HRR | 0.3 | **0.68** |

Formula: `relevance = 0.32 * (0.6*fts_rank + 0.4*jaccard) + 0.68 * hrr_sim`

Insight: on a clean curated corpus, semantic recall (HRR) outperforms keyword matching.

### L5: Injection Budget Enforcement
Hard caps applied during `FactRetriever.search()` after scoring:
```
max_injected_items          = 3
max_memory_chars_per_item   = 200
max_injected_chars_total    = 880
```
Per-item: use `summary` field if available, else truncate.
Per-recall: track over_budget_count for quality_metrics.

This is the **direct fix for signal 9 / OOM**.

### L6: Agent/User Profile Weighting
```python
_AGENT_PROFILES = {
    "default":  {"lexical": 0.32, "hrr": 0.68, "max_items": 3, "max_chars": 880},
    "xiaoa":    {"lexical": 0.25, "hrr": 0.75, "max_items": 4, "max_chars": 1100},
    "openclaw": {"lexical": 0.55, "hrr": 0.45, "max_items": 3, "max_chars": 880},
}
```
API: `provider.search_with_profile(query, agent_id="xiaoa")`

### L8: Health Check Endpoint
`provider.health_check()` returns: db_size, active_count, avg_memory_chars,
vector_count, latest_metrics, last_compact, lcm_dag status, upgrade recommendations.

## Key Files

| File | Role |
|------|------|
| `plugins/memory/holographic/store.py` | Schema, CRUD, compact, quality_metrics |
| `plugins/memory/holographic/retrieval.py` | Hybrid recall + budget enforcement |
| `plugins/memory/holographic/__init__.py` | Provider, profiles, health_check |

## Verification

```bash
python3 -c "
import sys; sys.path.insert(0, 'hermes-agent')
from plugins.memory.holographic import HolographicMemoryProvider as P
p = P(); p.initialize('v')
print(p.health_check())
r = p.search_with_profile('刘小豪', agent_id='xiaoa')
for f in r: print(f['score'], f['content'][:60])
"
```

## Known Gaps

- **L7** (Ollama + bge-m3 + FAISS): not yet implemented. Needed when facts > 500.
- **LCM DAG depth**: `LCM_INCREMENTAL_MAX_DEPTH=-1` not set → add to bashrc and restart gateway
- **compact cron**: not yet scheduled — add via `cronjob` tool calling `compact_facts()`
