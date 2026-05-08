# Source: `trigger-log-autobind`

---
name: trigger-log-autobind
description: "AutoHotkey 式触发日志 — 追踪记忆/技能/任务的激活频率，高频自动晋升绑定。通用机制，可集成到任意记忆系统。"
category: system
tags: [memory, trigger, frequency, autobind, autohotkey]
trigger: [触发日志, 频率追踪, 自动晋升, autobind, trigger log]
dependencies: []
---

# AutoHotkey 式触发日志

## 核心思想

每次记忆被激活（enter/trigger/search），记录一条触发事件。统计时间窗口内各记忆的触发频率，高频触发的记忆自动绑定到目标系统的空闲槽位。

```
触发事件（enter/trigger/search）
    ↓
记录 → trigger_log.json
    ↓
每4小时 auto-bind 扫描
    ↓
时间窗口内触发 >= 阈值
    ↓
自动绑定到空闲桩位
    ↓
promotions 列表记录晋升历史
```

## 核心参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `MAX` | 30 | 保留最近 N 条触发记录（循环覆盖） |
| `WINDOW_HOURS` | 48 | 统计时间窗口（小时） |
| `MIN_FREQ` | 2 | 自动绑定阈值（触发 N 次以上） |

## 实现代码

```python
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

class TriggerLog:
    """AutoHotkey 式触发日志"""

    MAX = 30
    WINDOW_HOURS = 48
    MIN_FREQ = 2

    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log = self._load()

    def _load(self):
        if self.log_path.exists():
            with open(self.log_path) as f:
                return json.load(f)
        return {"triggers": [], "promotions": []}

    def _save(self):
        with open(self.log_path, "w") as f:
            json.dump(self.log, f, indent=2, ensure_ascii=False)

    def record(self, item_id: str, trigger_type: str,
               room_id: str = None, loci_name: str = None):
        """
        记录一次触发事件
        - item_id: 被触发的记忆/技能/任务 ID
        - trigger_type: "enter" | "trigger" | "search" | "walk"
        """
        entry = {
            "item_id": str(item_id),
            "type": trigger_type,
            "room": room_id,
            "loci": loci_name,
            "ts": datetime.now().isoformat(),
        }
        self.log["triggers"].append(entry)

        # 循环覆盖
        if len(self.log["triggers"]) > self.MAX * 2:
            self.log["triggers"] = self.log["triggers"][-self.MAX:]

        self._save()
        return entry

    def frequency(self, window_hours: int = None) -> dict:
        """返回 {item_id: 触发次数}"""
        wh = window_hours or self.WINDOW_HOURS
        cutoff = datetime.now() - timedelta(hours=wh)
        recent = []
        for t in self.log["triggers"]:
            ts = t.get("ts") or t.get("timestamp", "")
            if not ts:
                continue
            try:
                if datetime.fromisoformat(ts) >= cutoff:
                    recent.append(t)
            except ValueError:
                continue
        return dict(Counter(t["item_id"] for t in recent).most_common())

    def candidates(self, bound_ids: set, min_freq: int = None) -> list:
        """
        返回可自动绑定的高频候选
        - bound_ids: 已被绑定的 item_id 集合（避免重复绑定）
        """
        mf = min_freq or self.MIN_FREQ
        freq = self.frequency()
        result = []
        for item_id, count in freq.items():
            if count >= mf and item_id not in bound_ids:
                result.append({"item_id": item_id, "count": count})
        result.sort(key=lambda x: x["count"], reverse=True)
        return result

    def promote(self, item_id: str, room_id: str, loci_id: str):
        """记录一次晋升"""
        self.log["promotions"].append({
            "item_id": item_id,
            "room": room_id,
            "loci": loci_id,
            "ts": datetime.now().isoformat(),
        })
        self._save()
```

## 使用模式

### 模式1：集成到 CLI 工具

在 CLI 的 enter/walk/trigger 命令中自动调用：

```python
def enter_room(self, room_id: str, record_trigger: bool = True):
    # ... 原有逻辑 ...
    if record_trigger:
        self.trigger_log.record(
            mem_id,
            "enter",
            room_id,
            loci["name"]
        )
```

### 模式2：绑定逻辑

```python
def auto_bind(self, target_system, cat_to_room: dict, top_n: int = 3):
    """
    - target_system: 有 load()/save() 和 rooms 结构的对象
    - cat_to_room: category → room_id 映射
    """
    bound_ids = set(target_system.bindings.keys())
    cands = self.candidates(bound_ids)

    promoted = []
    for cand in cands[:top_n]:
        item_id = cand["item_id"]
        # 根据 item 类别找目标房间
        cat = get_category(item_id)  # 你需要自己实现
        room_id = cat_to_room.get(cat, "library")

        # 找空闲桩位
        room = target_system.palace[room_id]
        free = [l for l in room["loci"] if l["bound_item_id"] is None]
        if not free:
            continue

        loci = free[0]
        loci["bound_item_id"] = item_id
        target_system.bindings[item_id] = {"room": room_id, "loci": loci["id"]}
        self.promote(item_id, room_id, loci["id"])
        promoted.append(cand)

    target_system.save()
    return promoted
```

## 在 Hermes 中的已部署实例

```
~/.hermes/memory_palace/
├── trigger_log.json       # 触发日志
└── memory_palace.py       # TriggerLog 已内置

~/.hermes/evolution_logs/skill_optimizer/
└── dojo.py               # Step 7 调用 distill_findings_to_memory()
```

## Cron 注册

```
memory-palace-autobind  */4h  auto_bind(top_n=3)
```

## 关键坑点

1. **时间戳格式兼容**：旧日志可能用 `timestamp` 字段而非 `ts`，需要 `t.get("ts") or t.get("timestamp", "")`
2. **绑定冲突**：hardcoded 目标桩会导致多记忆互相覆盖，应该找空闲桩
3. **循环缓冲**：超过 MAX*2 条时裁剪到 MAX 条，而不是清空
