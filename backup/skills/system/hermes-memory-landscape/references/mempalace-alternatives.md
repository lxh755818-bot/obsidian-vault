# Source: `mempalace-alternatives`

---
name: mempalace-alternatives
description: "Android/Termux AI memory landscape: Hermes has built-in SQLite+FTS5 memory (1149 msgs indexed, active). External packages (MemPalace/memvid/mem0/mem9) all fail due to native compilation requirements — use Hermes built-ins instead."
version: 1.0.0
author: Hermes Agent
tags: [memory, android, termux, aarch64]
prerequisites: [native-mcp]
---

# AI Memory Systems on Android/Termux (aarch64)

## Problem

MemPalace and most AI memory systems depend on **native compiled extensions** that fail on Android/Termux:

| Package | Blocker | Error |
|---------|---------|-------|
| mempalace / chromadb | Rust (chroma-hnswlib) | maturin/cargo not available |
| memvid | cmake + opencv-python | Build failed |
| mem0 / mem0ai | Timeout / not found on PyPI | — |

**Root cause**: chroma-hnswlib (Rust), opencv-python (cmake/C++) require cross-compilation toolchain for aarch64.

## Cross-Compilation Reality Check

- ChromaDB's `chroma-hnswlib` is Rust → needs `cargo` with aarch64 target
- opencv-python needs cmake + C++ toolchain
- Termux has `clang` but no Rust toolchain by default
- Android NDK cross-compilation for Python packages is extremely complex
- **Verdict: NOT worth the effort**

## What Actually Works

### Hermes Built-in Memory (✅ PRIMARY — already running, use this first)

Hermes Agent has a **built-in 4-layer memory system** that requires no external packages. On Android/Termux this is already active:

| Layer | Storage | Location | Status |
|-------|---------|----------|--------|
| L1: Persistent context | MEMORY.md + USER.md | `~/.hermes/memories/` | ✅ Active |
| L2: Session archive | SQLite + FTS5 | `~/.hermes/state.db` | ✅ 1149 msgs indexed |
| L3: Skill library | SKILL.md files | `~/.hermes/skills/` | ✅ Active |
| L4: Evolution logs | JSON benchmarks | `~/.hermes/evolution_logs/` | ✅ Active |

**Verified on this environment:**
- `state.db` tables: `sessions`, `messages`, `messages_fts` (full-text index)
- 14 sessions archived, 1149 messages in FTS index
- MEMORY.md / USER.md auto-loaded per session (~3575 char limit each)
- evolution_logs contains skill_optimizer + error_correction benchmarks

**Key insight: Do NOT install external memory packages on Android/Termux. Use Hermes's built-in system first.**

### SQLite + Python Standard Library (✅ Fallback — if custom memory needed)

If additional memory features are required beyond Hermes built-ins, build using only Python stdlib:

```python
import sqlite3  # Native, no build
import json     # Native
import difflib  # Native - for similarity search
```

**Strategy**: Custom memory palace using SQLite as store + difflib for retrieval. No vectors, no native deps.

### Omni-SimpleMem / simplemem (❌ Fails on Termux)

GitHub: `aiming-lab/SimpleMem` — 3.2k stars, MIT, v0.2.0 Omni supports multimodal

**Actual PyPI package**: `simplemem==0.1.0` — BUT dependencies all fail on Termux/aarch64:

| Dependency | Status | Blocker |
|-----------|--------|---------|
| `lancedb>=0.4.0` | ❌ | `pylance` package does not exist on PyPI; `lance` PyPI package conflicts |
| `sentence-transformers>=2.2.0` | ❌ | Requires `torch>=2.0.0`, no aarch64 PyPI wheel |
| `tantivy>=0.20.0` | ❌ | Rust-based full-text engine, needs rustc toolchain |
| `pyarrow>=12.0.0` | ⚠️ | Termux `pkg install python-pyarrow` works, but lancedb still fails |
| `torch` | ❌ | No PyPI wheel for aarch64/Android |
| `numpy` | ❌ | No precompiled wheel for Python 3.13 aarch64 |
| `openai>=1.0.0` | ✅ | Works, but irrelevant without embedding backend |

**Key discovery**: LanceDB has a naming conflict on PyPI — the package `lance` is a different project (not LanceDB's core). The actual LanceDB Python bindings are `lancedb` which internally requires `pylance` (doesn't exist) or needs building from source with Rust.

**Verdict**: NOT installable on Termux/Android aarch64.

### MiniMax Embedding API (⚠️ Viable but need balance)

MiniMax `embo-01` embedding API works from Termux (认证通过):
- Endpoint: `https://api.minimaxi.com/v1/embeddings`
- Model: `embo-01`
- **Current status**: `status_code: 1008, insufficient balance` — account needs top-up
- If balance is restored, this is the most viable path for embedding on Termux

### sqlite-vss (❌ No aarch64 wheel)

PyPI only has wheels for: `manylinux_2_17_x86_64`, `macosx_11_0_arm64`, `macosx_10_6_x86_64`
**No aarch64/Android wheel available.**

### mem9 (⚠️ Viable as hosted fallback for cross-agent memory)

GitHub: `mem9-ai/mem9` — "Unlimited memory for OpenClaw"
GitHub: `mem9-ai/mem9-hermes-plugin` — 官方 Hermes 插件

**2026-04-27 更新**：mem9 不再是"仅 REST 服务器"，已有专用 Hermes 插件：
```bash
hermes plugins install
plugins/memory/mem9
# 配置 MEM9_API_KEY 到 ~/.hermes/.env
# 即可激活，零代码
```

**mem9 价值**：
- 跨 Agent 记忆共享（Hermes ↔ OpenClaw ↔ Claude Code ↔ Codex）
- 自动从对话提取 facts（无需手动 fact_store）
- 可视化 Dashboard
- TiDB 后端（可选自托管）

**mem9 不替代 Holographic Phase 2**：
- Holographic：本地 SQLite，无需网络，HRR 代数推理
- mem9：外部 API，跨 Agent，自动提取，但依赖网络

**结论**：Holographic Phase 2 已足够；mem9 作为跨 Agent 共享的可选备选。

## Recommended Implementation Plan

A `mempalace-simple` skill using:

- **Storage**: SQLite (wing/hall/room/closet/drawer schema)
- **Retrieval**: difflib SequenceMatcher for similarity + keyword index
- **MCP interface**: Expose as stdio MCP server via `python -m <module>`
- **Schema**:
  ```sql
  CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    wing TEXT, hall TEXT, room TEXT,
    content TEXT, embedding_id TEXT,
    created_at REAL
  );
  CREATE INDEX idx_nav ON memories(wing, hall, room);
  CREATE INDEX idx_content ON memories(content);
  ```

## Verified Available on Termux Python 3.13

- ✅ sqlite3, json, difflib, hashlib, pathlib (stdlib)
- ❌ numpy, scipy (no aarch64 wheel for Python 3.13)
- ❌ sentence-transformers, torch, lancedb, tantivy (heavy deps)
- ❌ sqlite-vss (no aarch64 wheel)
- ⚠️ MiniMax `embo-01` embedding API works but needs account balance

## Environment

```
Platform: Android-16-aarch64-64bit (Termux)
Python: 3.13.13
pip: 26.0.1
Venv: ~/.mempalace-venv
```
