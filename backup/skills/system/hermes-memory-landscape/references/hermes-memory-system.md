# Source: `hermes-memory-system`

---
name: hermes-memory-system
description: Hermes 分层记忆系统 - 管理、分层、压缩和检索长期记忆
category: system
tags: [memory, hierarchy, compression, supervisor]
version: 1.1.0
last_updated: 2026-04-22
---

# Hermes 分层记忆系统

## 架构概览

```
Hermes 记忆系统采用分层索引架构:
├── L0: MEMORY.md (根索引) — 始终 < 5KB
├── L1: memories/[domain]/ — 域索引 (7个域)
└── L2: memories/[domain]/*.md — 具体记忆文件

辅助目录:
├── .dirty/ — 待整理的原始记忆
├── .archive/ — 归档的原始文件
└── index.json — 系统索引
```

## 目录结构

| 域 | 路径 | 说明 |
|---|---|---|
| skills | `memories/skills/` | 技能系统、工具使用记忆 |
| user | `memories/user/` | 用户信息、关系、偏好 |
| projects | `memories/projects/` | 项目记录、任务追踪 |
| topics | `memories/topics/` | 话题讨论、研究调研 |
| preferences | `memories/preferences/` | 用户偏好设置 |
| errors | `memories/errors/` | 错误记录与解决方案 |
| workflows | `memories/workflows/` | 工作流程、最佳实践 |

## 容量规则

| 层级 | 硬上限 | 软上限 | 淘汰策略 |
|---|---|---|---|
| **L0** MEMORY.md | 5KB | 3KB | 仅保留最精华摘要 |
| **L1** 各域 | 50KB | 30KB | 90-120天LRU |
| **L2** 单文件 | 20KB | 15KB | 超限自动拆分 |

## 淘汰规则

- **< 90 天**: 正常保留，不删除
- **90-120 天**: LRU 淘汰，调用时刷新时间（最多刷新 3 次）
- **> 120 天**: 硬删除，不管频率

## 压缩规则

- **压缩比例**: 保留 40-50%，压缩 40-50%
- **必留内容**: 完整指令、文件路径、参数命令、数字配置、日期时间
- **可删内容**: 语气词、重复表达、废话铺垫、情绪表达

详细规则见: `~/.hermes/memories/.compression_rules.md`

---

## 脚本工具

### Supervisor (内存管理模块)

```bash
python ~/.hermes/scripts/memory_supervisor.py [action]
```

Actions:
- `check` — 检查状态，不执行任何操作
- `status` — 输出记忆系统状态摘要
- `process` — 处理 dirty queue 中的待整理记忆
- `rebuild` — 重建整个 index（扫描所有文件）

### Compression Agent (压缩模块)

```bash
python ~/.hermes/scripts/compression_agent.py <file_path> <domain>
```

Example:
```bash
python ~/.hermes/scripts/compression_agent.py .dirty/session-123.md skills
```

---

## 添加新记忆

将原始记忆写入 `.dirty/` 目录，命名格式: `{session-id}.md`

```bash
echo "# 记忆内容" > ~/.hermes/memories/.dirty/session-123.md
```

---

## 查询记忆

### 方法 1: 直接读取 index

```bash
cat ~/.hermes/memories/index.json
```

### 方法 2: 读取 L1 域

```bash
cat ~/.hermes/memories/projects/*.md
```

### 方法 3: 全文搜索

```bash
grep -r "关键词" ~/.hermes/memories/
```

---

## 手动触发整理

```bash
# 1. 检查当前状态
python ~/.hermes/scripts/memory_supervisor.py check

# 2. 重建索引
python ~/.hermes/scripts/memory_supervisor.py rebuild

# 3. 处理 dirty queue
python ~/.hermes/scripts/memory_supervisor.py process
```

---

## Cron 集成

建议的 cron 配置:

```bash
# 每 2 小时检查一次状态
0 */2 * * * python ~/.hermes/scripts/memory_supervisor.py check >> ~/.hermes/cron/memory-check.log 2>&1

# 每天凌晨 3 点重建索引
0 3 * * * python ~/.hermes/scripts/memory_supervisor.py rebuild >> ~/.hermes/cron/memory-rebuild.log 2>&1

# 每 6 小时处理 dirty queue
0 */6 * * * python ~/.hermes/scripts/memory_supervisor.py process >> ~/.hermes/cron/memory-process.log 2>&1
```

---

## 故障恢复

### 备份

```bash
BACKUP_DIR=~/hermes-backup-$(date +%Y%m%d-%H%M%S)
mkdir -p $BACKUP_DIR
cp -r ~/.hermes/memories $BACKUP_DIR/
cp ~/.hermes/state.db $BACKUP_DIR/
```

### 从备份恢复

```bash
# 停止当前服务
# 恢复文件
cp -r ~/hermes-backup-YYYYMMDD-HHMMSS/memories/* ~/.hermes/memories/
# 重启服务
```

### Index 损坏时

```bash
python ~/.hermes/scripts/memory_supervisor.py rebuild
```

---

## 状态定义

- `active`: 正常使用的域
- `archiving`: 正在归档中
- `archived`: 已归档，不再活跃

---

## Termux/Android 向量搜索包安装结果

以下包在 Termux (Python 3.13, aarch64) 上**全部不可用**：

| 包 | 原因 |
|----|------|
| `lancedb` | `pylance` 包不存在 PyPI；`lance` PyPI 包名冲突 |
| `sentence-transformers` | 依赖 `torch`，PyPI 无 aarch64 wheel |
| `torch` | PyPI 完全没有 aarch64 预编译包 |
| `sqlite-vss` | 只有 Linux x86_64 + macOS wheel |
| `tantivy` | Rust 写的，需要 rustc 编译 |
| `ONNXRuntime` | PyPI 无 aarch64 wheel |
| `faiss-cpu` | 无 aarch64 预编译 |

**可行替代：**
- MiniMax `embo-01` Embedding API（API Key 存于飞书表格，余额不足时返回 1008）
- SQLite **FTS5** 全文搜索（内置，零依赖，`memory.db` 已在用）
- ChromaDB（待验证，自带 embedding）

**Omni-SimpleMem（`aiming-lab/SimpleMem`）**：v0.2.0，3.2k Stars，MIT。依赖 lancedb + sentence-transformers + tantivy，Termux 装不了。PyPI 包 `simplemem` v0.1.0 同样依赖 lancedb。

## 已知限制

1. 压缩不可逆，原始细节压缩后无法恢复
2. Supervisor 崩溃可能导致 dirty queue 丢失（下次启动时重新扫描）
3. 建议定期备份 memories 目录
4. 向量语义搜索在 Termux 暂不可用，需依赖 MiniMax Embedding API（余额充足）或纯 FTS5 全文搜索

---

*最后更新: 2026-04-22*
