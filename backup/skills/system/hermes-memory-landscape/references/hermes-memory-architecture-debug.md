# Source: `hermes-memory-architecture-debug`

---
name: hermes-memory-architecture-debug
description: 调试 Hermes Agent 重启后记忆丢失问题 — 核心发现 BuiltinMemoryProvider 文档有代码无，MemoryManager 只在配置 memory.provider 时才创建
triggers:
  - "重启后忘记记忆"
  - "记忆系统不生效"
  - "LCM session 不持久"
  - "gateway restart memory lost"
tags:
  - hermes-agent
  - memory
  - debug
  - architecture
category: system
created: 2026-04-27
---

# Hermes Agent 记忆系统架构调试技能

## 核心发现（2026-04-27 实测）

### 1. BuiltinMemoryProvider 是文档承诺，非实际实现

**文档**（memory_manager.py 第7行）：
> "The BuiltinMemoryProvider is always registered first and cannot be removed"

**实际代码**（run_agent.py 第1605-1661行）：
- `MemoryManager` 只在 `_mem_provider_name`（即 `config.yaml` 中的 `memory.provider`）有值时才创建
- **不配置 `memory.provider` = MemoryManager 从未被创建**
- BuiltinMemoryProvider 的代码从未在任何地方被实例化

```python
# run_agent.py 关键逻辑
if _mem_provider_name:   # ← 只有配置了这个才会走记忆逻辑
    from agent.memory_manager import MemoryManager
    self._memory_manager = _MemoryManager()
    _mp = _load_mem(_mem_provider_name)  # honcho/holographic/hindsight
```

### 2. config.yaml 中的 memory_* 配置只是限制，不是系统

```yaml
memory_enabled: true      # 标志位，不触发 MemoryManager
user_profile_enabled: true
memory_char_limit: 2200  # 截断限制，不是记忆本身
user_char_limit: 1375
```

### 3. 五个记忆层的实际状态

| 层级 | 系统 | 是否自动加载到新session | 问题 |
|------|------|------|------|
| LCM | 会话压缩 | ❌ 否 | 只在同session内压缩，重启后新session不加载 |
| fact_store | 结构化事实 | ❌ 否 | 1条fact，无自动召回逻辑 |
| Hindsight | 云端同步 | ❌ 否（已禁用） | 不在plugins enabled，欠费402 |
| Memory Palace | 记忆宫殿 | ❌ 否 | 桩位绑定，不自动触发 |
| MEMORY.md | 文本持久 | ❌ 否 | 需人工读取注入 |

---

## 诊断步骤

### Step 1：确认 MemoryManager 是否创建
```bash
grep -n "Memory provider" ~/.hermes/logs/agent.log
# 有 "Memory provider 'xxx' activated" = MemoryManager 已创建
# 无输出 = MemoryManager 从未创建
```

### Step 2：确认 memory.provider 配置
```bash
grep -n "memory.provider\|provider:" ~/.hermes/config.yaml
```

### Step 3：检查各记忆层数据库
```bash
# LCM summary nodes
python3 -c "
import sqlite3
conn = sqlite3.connect('$HOME/.hermes/lcm.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM summary_nodes')
print('Summary nodes:', cur.fetchone()[0])
cur.execute('SELECT COUNT(*) FROM messages')
print('Total messages:', cur.fetchone()[0])
conn.close()
"

# fact_store
python3 -c "
import sqlite3
conn = sqlite3.connect('$HOME/.hermes/memory_store.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM facts')
print('Facts:', cur.fetchone()[0])
conn.close()
"
```

### Step 4：检查 session_id 是否变化
LCM lifecycle_state 表中 session_id 以时间戳命名，每次重启极大概率产生新 id。

---

## 解决方案

### 方案A：配置 Honcho（推荐，本地向量记忆）
```bash
# 检查 honcho 是否可用
ls ~/hermes-agent/plugins/memory/honcho/
```
在 config.yaml 添加：
```yaml
memory:
  provider: honcho
```

### 方案B：配置 Holographic（轻量本地）
```yaml
memory:
  provider: holographic
```

### 方案C：手动实现持久记忆注入
在 session 开始时读取 MEMORY.md + USER.md + fact_store，注入到 system prompt。
需自定义 BuiltinMemoryProvider 或使用 on_session_end/on_turn_start hook。

---

## 验证修复
1. 重启网关：`hermes gateway restart`
2. 检查日志：`grep "Memory provider" ~/.hermes/logs/agent.log`
3. 新 session 开始时发送测试消息，观察是否提及历史内容
