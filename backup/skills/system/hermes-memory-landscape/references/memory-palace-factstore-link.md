# Source: `memory-palace-factstore-link`

# Memory Palace ↔ fact_store 联动系统

> 版本: v1.0 | 创建: 2026-04-27

## 触发条件

- "联动记忆宫殿和fact_store"
- "建立记忆系统协同"
- "高价值fact绑定到宫殿"
- "记忆宫殿和事实库同步"

## 背景

当前记忆系统有 **3个独立层**：

```
fact_store (memory_store.db)
  └── 3 facts，HRR向量嵌入，trust评分
  └── 与宫殿完全独立

记忆宫殿 (memory_palace.py)
  └── 6房间/37桩位，13个binding
  └── bindings.json 里的 mem_id 实际是假ID（指向不存在的fact）
  └── trigger_log 记录 enter/trigger/walk 事件

LCM DAG (lcm.db)
  └── 18个D0节点，0个D1+节点
  └── 与另外两系统完全独立
```

## 联动目标

让 fact_store 中的高价值发现**自动同步到记忆宫殿**，形成统一记忆层。

## 联动机制

### 写入路径（fact_store → palace）

高价值fact自动绑定到对应房间的空闲桩位：

| fact category | → 记忆宫殿房间 |
|---------------|---------------|
| skill/workflow | workshop (工坊) |
| project | archive (档案室) |
| system/gateway | command_center (指挥中心) |
| person/relationship | garden (秘密花园) |
| knowledge/research | library (图书馆) |
| general | 入口大厅 |

### 绑定规则

1. **自动晋升**: fact 被检索 `≥3次` 且 `trust_score ≥ 0.6` → 绑定到宫殿
2. **手动触发**: 用户说"记住这个" → 立即绑定
3. **绑定位置**: 优先选择 `bound_memory_id=null` 的空闲桩位

### 实现代码

```python
#!/usr/bin/env python3
"""
fact_store → memory_palace 联动脚本
将高价值fact绑定到记忆宫殿桩位
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

HERMES = Path.home()
MEMORY_STORE = HERMES / ".hermes/memory/memory_store.db"
PALACE_MAP = HERMES / ".hermes/memory_palace/palace_map.json"
BINDINGS = HERMES / ".hermes/memory_palace/bindings.json"

def get_high_value_facts(conn, min_retrievals=3, min_trust=0.6):
    """获取高价值fact（满足绑定条件）"""
    cur = conn.execute(
        "SELECT fact_id, content, category, tags, trust_score, retrieval_count "
        "FROM facts WHERE retrieval_count >= ? AND trust_score >= ?",
        (min_retrievals, min_trust)
    )
    return list(cur.fetchall())

def get_room_for_category(category):
    """根据fact类别返回对应宫殿房间"""
    mapping = {
        "skill": "workshop",
        "workflow": "workshop",
        "project": "archive",
        "system": "command_center",
        "person": "garden",
        "relationship": "garden",
        "knowledge": "library",
        "research": "library",
        "general": None,  # 入口大厅
    }
    return mapping.get(category)

def find_free_loci(palace_map, room_id):
    """找房间内第一个空闲桩位"""
    room = palace_map.get(room_id, {})
    for loci in room.get("loci", []):
        if loci.get("bound_memory_id") is None:
            return loci["id"]
    return None

def sync_factstore_to_palace():
    """主同步函数"""
    # 1. 读取宫殿数据
    palace_map = json.loads(PALACE_MAP.read_text())
    bindings = json.loads(BINDINGS.read_text())
    
    # 2. 连接 fact_store
    conn = sqlite3.connect(MEMORY_STORE)
    facts = get_high_value_facts(conn)
    conn.close()
    
    # 3. 对每个高价值fact尝试绑定
    results = []
    for fact_id, content, category, tags, trust, retrievals in facts:
        room_id = get_room_for_category(category)
        if not room_id:
            continue
        
        free_loci = find_free_loci(palace_map, room_id)
        if not free_loci:
            continue
        
        # 避免重复绑定
        if str(fact_id) in bindings:
            continue
        
        # 绑定
        bindings[str(fact_id)] = {
            "room": room_id,
            "loci": free_loci
        }
        # 更新 palace_map
        for loci in palace_map[room_id]["loci"]:
            if loci["id"] == free_loci:
                loci["bound_memory_id"] = str(fact_id)
                break
        
        results.append({
            "fact_id": fact_id,
            "room": room_id,
            "loci": free_loci,
            "content_preview": content[:50]
        })
    
    # 4. 写回
    BINDINGS.write_text(json.dumps(bindings, indent=2, ensure_ascii=False))
    PALACE_MAP.write_text(json.dumps(palace_map, indent=2, ensure_ascii=False))
    
    return results

if __name__ == "__main__":
    results = sync_factstore_to_palace()
    if results:
        print(f"✅ 联动成功: {len(results)} 个fact绑定到宫殿")
        for r in results:
            print(f"  fact_id={r['fact_id']} → {r['room']}/{r['loci']}")
    else:
        print("ℹ️ 无需联动（无高价值fact或所有桩位已满）")
```

## 使用方式

```bash
# 手动执行联动
python3 ~/.hermes/memory_palace/factstore_sync.py

# 或通过记忆宫殿 CLI
python3 ~/.hermes/memory_palace/memory_palace.py auto-bind
```

## 触发时机

1. **dojo.py 每日运行时** — Step 7 记忆沉淀后自动执行
2. **skill-cycle-optimizer 完成后** — 高评分技能自动沉淀
3. **用户明确要求时** — "记住这个"
4. **每4小时 trigger_log auto-bind** — 高频触发记忆自动晋升

## 验证方法

```python
python3 -c "
import json
b = json.load(open('~/.hermes/memory_palace/bindings.json'))
print(f'已绑定记忆数: {len(b)}')
for fid, binding in b.items():
    print(f'  fact_id={fid} → {binding}')
"
```
