# Source: `self-memory-system-inspection`

---
name: self-memory-system-inspection
description: 系统化诊断自身记忆系统架构的方法论——检查LCM/LCM/fact_store/Hindsight/记忆宫殿/memories各层状态，输出完整架构报告
triggers:
  - "检查记忆系统"
  - "分析自身记忆"
  - "诊断记忆"
  - "记忆系统汇报"
  - "memory system inspection"
---

# 自我记忆系统诊断技能

## 触发条件
- 用户要求"检查/分析/诊断"自身记忆系统
- 需要汇报记忆系统现状和问题
- 需要找出记忆系统的配置问题或失效模块

## 诊断路径（按顺序执行）

### 1. LCM 状态
```python
# 使用 lcm_status 工具获取压缩引擎状态
lcm_status()

# 检查 lcm.db 数据库
python3 -c "
import sqlite3
conn = sqlite3.connect('/data/data/com.termux/files/home/.hermes/lcm.db')
cur = conn.cursor()
cur.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')
print([r[0] for r in cur.fetchall()])
cur.execute('SELECT COUNT(*) FROM messages')
print(f'messages: {cur.fetchone()[0]}')
conn.close()
"
```

### 2. fact_store 状态
```python
python3 -c "
import sqlite3
conn = sqlite3.connect('/data/data/com.termux/files/home/.hermes/memory_store.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM facts')
print(f'facts: {cur.fetchone()[0]}')
cur.execute('SELECT COUNT(*) FROM entities')
print(f'entities: {cur.fetchone()[0]}')
cur.execute('SELECT COUNT(*) FROM memory_banks')
print(f'memory_banks: {cur.fetchone()[0]}')
conn.close()
"
```

### 3. 记忆宫殿状态
```bash
cat ~/.hermes/memory_palace/palace_map.json
cat ~/.hermes/memory_palace/bindings.json
cat ~/.hermes/memory_palace/trigger_log.json
```

### 4. Hindsight 配置和同步状态
```bash
cat ~/.hermes/hindsight/config.json
grep -n "hindsight" ~/.hermes/logs/agent.log | tail -20
```

### 5. memories/ 文本层
```bash
cat ~/.hermes/memories/MEMORY.md
cat ~/.hermes/memories/USER.md
cat ~/.hermes/memories/index.json
```

### 6. 关键配置文件
```bash
grep -A 20 "^memory:" ~/.hermes/config.yaml
grep -A 20 "^plugins:" ~/.hermes/config.yaml
```

## 已知问题模式（快速检查清单）

| 问题 | 检查方式 | 配置文件 |
|------|---------|---------|
| Hindsight 402欠费 | `grep hindsight ~/.hermes/logs/agent.log` | `~/.hermes/hindsight/config.json` |
| DAG层级凝结未触发 | `lcm_status()` 看 `depths` 是否全为0 | condensation_fanin=4（需同session同深度≥4节点才触发） |
| DAG配置是否生效 | `lcm_status()` 看 `max_depth` | config.py第55行默认值是-1（非1） |
| fact_store空转 | 查询 facts 表数量 | `~/.hermes/memory_store.db` |
| state.db过大 | `ls -lh ~/.hermes/state.db` | — |
| 记忆宫殿桩位空置 | `bindings.json` 中 null 数量 | `~/.hermes/memory_palace/` |

### ⚠️ DAG深度判断的关键纠正（2026-04-27）
- `max_depth` 显示的是**配置值**，不是实际凝结层数
- `lcm_status` 的 `depths` 字段显示实际各层节点数，**全部为0才说明凝结未触发**
- 凝结触发条件：`condensation_fanin=4`（需同session同深度节点≥4个）
- 历史节点分散在多个不同session会导致fanin永远凑不够，这是**数据碎片化**现象，非配置问题
- 新session会正常累积，凝结在context满时自动触发

## 输出格式模板

```
# 🧠 [Agent名] 记忆系统完整架构报告

## 一、总体架构：N层并行
[各层概览表格]

## 二、各层详情
[每层的关键指标表格]

## 三、关键问题汇总
| # | 问题 | 严重度 |
[问题列表]

## 四、建议优先级
[按优先级排序的Action Items]
```

## 注意事项
- LCM DAG depth 正常情况下应该 >1，如果 max_depth=1 配置存在但 depth=1，说明压缩没有形成层级结构
- fact_store 和记忆宫殿是两个独立系统，需要手动联动（bindings.json）
- Hindsight 同步失败会导致云端记忆丢失，但不影响本地 LCM 和 fact_store
- Termux 下 Python 用 `python3` 而非 `python`，sqlite3 命令行不可用需用 Python 查询
