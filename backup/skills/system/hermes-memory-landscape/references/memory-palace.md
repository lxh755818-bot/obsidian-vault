# Source: `memory-palace`

---
name: memory-palace
description: 记忆宫殿技能 — 场景记忆法实现，通过物理空间隐喻管理记忆。6个房间/37个桩位，支持enter/walk/trigger/bind操作。与semantic.db打通，记忆自动绑定到桩位。
category: system
tags: [memory, palace, spatial, loci, recall]
trigger: [记忆宫殿, 场景记忆, palace, loci, spatial recall]
dependencies: []
---

# 记忆宫殿 (Memory Palace)

## 核心原理

**记忆宫殿法**（Method of Loci）：将信息锚定在熟悉的空间位置，通过"空间行走"激活记忆。比线性列表更容易记住，因为人脑进化出强大的空间导航能力。

## 物理结构

```
~/.hermes/memory_palace/
├── palace_map.json     # 宫殿地图（6房间/37桩）
├── bindings.json       # 记忆ID→桩位 绑定表
└── memory_palace.py    # CLI 引擎

~/.hermes/memory/semantic.db  # 记忆存储（L3语义层）
```

## 6个房间

| 房间ID | 名称 | 桩数 | 职责 |
|--------|------|------|------|
| entrance | 入口大厅 | 5 | 今日状态/紧急任务 |
| workshop | 工坊 | 8 | 技能调试/错误记录 |
| library | 图书馆 | 8 | 知识积累/调研成果 |
| archive | 档案室 | 6 | 历史项目/已完成任务 |
| command_center | 指挥中心 | 5 | 系统状态/Gateway/Cron |
| garden | 秘密花园 | 5 | 人格核心/进化反思 |

## CLI 用法

```bash
# 宫殿概览
python ~/.hermes/memory_palace/memory_palace.py status

# 进入房间（定点激活）
python ~/.hermes/memory_palace/memory_palace.py enter workshop
python ~/.hermes/memory_palace/memory_palace.py enter command_center

# 随机漫步
python ~/.hermes/memory_palace/memory_palace.py walk 3

# 定点触发（关键词搜索）
python ~/.hermes/memory_palace/memory_palace.py trigger Gateway
python ~/.hermes/memory_palace/memory_palace.py trigger 选股

# 手动绑定记忆到桩位
python ~/.hermes/memory_palace/memory_palace.py bind 5 archive:2

# 添加新记忆（自动分配桩位）
python ~/.hermes/memory_palace/memory_palace.py add "baostock接口换了新域名" skill P1
```

## 场景化使用

### 场景1：进入工坊调试技能
```
用户: "我之前修复的那个MCP工具调用问题，现在用什么方式？"
→ python memory_palace.py trigger MCP
→ 激活 workshop/当前调试的技能 → 记忆5: "MiniMax图片识别走直接API，不走MCP工具"
→ 回答: "走直接API调用，不走MCP工具——之前踩坑记录过"
```

### 场景2：随机漫步激发创意
```
用户: "有什么新想法可以尝试？"
→ python memory_palace.py walk 3
→ 随机激活: library/竞品对比 + workshop/新想法
→ 结合两个记忆生成新洞察
```

### 场景3：指挥中心检查系统状态
```
用户: "现在Gateway还连着吗？"
→ python memory_palace.py enter command_center
→ 激活 command_center/所有桩位
→ 看到 Gateway PID 和 Cron状态 → 给出实时状态
```

## 与semantic.db的关系

```
semantic.db（记忆仓库）
    │
    ├── 记忆5: MiniMax图片API
    │       └── 绑定 → workshop/当前调试的技能
    ├── 记忆6: 选股系统
    │       └── 绑定 → archive/选股系统
    └── 记忆1: 刘小豪档案
            └── 绑定 → garden/主人档案
```

**原则**：记忆本体存在 semantic.db，宫殿只负责空间锚定。删除宫殿绑定不会删除记忆，删除记忆会自动清空绑定。

## 填充策略

当前 **12/37** 桩位已绑定（2026-04-26 晚），分布如下：

| 房间 | 绑定 | 桩位内容 |
|------|------|---------|
| 档案室 | 4/6 | 选股系统、xiaoa-persona-system 生成、peft 检修、skill-cycle-optimizer 规则 |
| 指挥中心 | 4/5 | Gateway PID、协作者、Cron、刘大虾 |
| 工坊 | 3/8 | MiniMax API、M3 架构、飞书密钥 |
| 秘密花园 | 1/5 | 刘小豪档案 |
| 入口大厅 | 0/5 | **应为动态读取，不绑定** |
| 图书馆 | 0/8 | 等调研输入 |

### 入口大厅的正确用法

入口大厅的 5 个桩是**实时状态**，不应该绑定静态记忆。应该在 `enter entrance` 时动态生成：

```
[1] 今日首要任务 → 读 cronjob list 找未完成的最近截止任务
[2] 待处理飞书   → 读飞书未读消息数
[3] 定时任务状态 → 读 cronjob list 全部状态
[4] Gateway连接  → ps + 日志最近3行
[5] 能量状态     → 读 evolution 日志最近评分
```

### 自动填充来源

- **每4小时 auto-bind**：高频触发记忆（>=2次/48h）自动晋升
- **每天 dojo 闭环**：分析报告自动沉淀到档案室
- **每周调研**：GitHub 趋势 → 图书馆
- **入口大厅**：始终动态读取，不沉淀

## AutoHotkey 式触发日志（核心机制）

每次记忆被激活（enter/trigger/walk）时自动记录触发事件，高频触发自动晋升绑定到宫殿桩位：

```
~/.hermes/memory_palace/
├── palace_map.json     # 6房间/37桩
├── bindings.json       # 记忆ID→桩位
├── trigger_log.json   # AutoHotkey 触发日志（NEW）
└── memory_palace.py   # CLI 引擎（含 TriggerLog 类）

~/.hermes/memory/daily_distill/  # 每日蒸馏（NEW）
```

### 触发日志工作流

```
触发事件（enter/trigger/walk）
    ↓
记录 → trigger_log.json
    ↓
每4小时 auto-bind Cron
    ↓
扫描48h内触发>=2次的记忆
    ↓
自动绑定到对应房间的空闲桩位
    ↓
promotions 列表记录晋升历史
```

### TriggerLog 类（memory_palace.py 内置）

```python
mp = MemoryPalace()  # 自动加载 trigger_log

# 触发自动记录（enter/walk/trigger 均自动记录）
mp.enter_room("workshop")     # → 记录触发
mp.random_walk(2)              # → 每激活一个记忆就记录
mp.trigger("选股")              # → 记录触发

# 手动查看频率
mp.trigger_log.frequency()     # → {mem_id: 触发次数}

# 手动触发自动绑定
mp.trigger_log.auto_bind(top_n=3, min_freq=2)  # 绑定>=2次的记忆
```

### 频率阈值（可调）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `MAX` | 30 | 保留最近30条触发记录 |
| `WINDOW_HOURS` | 48 | 统计窗口48小时 |
| `MIN_FREQ` | 2 | 自动绑定阈值 |

### Q1/Q2/Q3 决策框架

**每次写入记忆前必须先判断优先级**：

```
Q1: 下次醒来不看这条，会做错事吗？
  → Yes → [P0] 核心事实（永不过期）
  → No  → 继续 Q2

Q2: 某天可能需要查这条吗？
  → Yes → [P1] 潜在有用（90天后清理）
  → No  → [P2] 临时记录（30天后清理）

Q3: 以上都不是？
  → 不写入记忆，留在 daily_distill/
```

**判断示例**：
- `"刘小豪手机号18307655818"` → P0
- `"peft最新版本支持LoRA"` → P1
- `"今天测试接口延迟3ms"` → P2
- `"用户说下午好"` → 不写入

### 写入命令

```bash
python ~/.hermes/memory_palace/memory_palace.py add "记忆内容" <类别> [P0|P1|P2]
```

### 每日蒸馏（sessions → 每日摘要）

**脚本位置**：`~/.hermes/scripts/daily_distill.py`

**state.db schema 关键发现**：
- `messages.timestamp` 是 **Unix float**（秒级时间戳），不是 ISO 字符串
- 查询时必须用 `WHERE timestamp >= ?` 而非 `WHERE created_at >= ?`
- 正确用法：`cutoff_ts = datetime.now().timestamp() - hours * 3600`
- `memories.tokens` 是 **NOT NULL** 字段，写入时必须提供

```python
# 正确查询 recent messages（from daily_distill.py）
cutoff_ts = datetime.now().timestamp() - hours * 3600
messages = cur.execute("""
    SELECT id, session_id, role, content, timestamp
    FROM messages WHERE timestamp >= ?
    ORDER BY timestamp ASC
""", (cutoff_ts,)).fetchall()

# 正确写入 semantic.db（tokens 字段 NOT NULL）
cur.execute(
    "INSERT INTO memories (text,category,tokens,priority,access_count,created_at,last_accessed,ttl_days) "
    "VALUES (?,?,?,?,0,?,?,90)",
    (text, category, str(len(text)), "P1", datetime.now().isoformat(), datetime.now().isoformat())
)
```

### dojo → 记忆沉淀集成

hermes-dojo 闭环（`~/.hermes/evolution_logs/skill_optimizer/dojo.py`）的 Step 7 自动将分析报告写入 semantic.db：

```
dojo.py 流程：
  Step 1-5: Monitor → Analyzer → Fixer → Reporter → Learning Curve
  Step 6: Auto-Fixer dry-run
  Step 7: distill_findings_to_memory() ← 分析报告 → 记忆 + 绑定桩位
  Step 8: 飞书推送
```

**distill_findings_to_memory 逻辑**：
- 读取 `improvement_plan.json`（analyzer 输出）
- 对每个评分 >= 4 的技能决策（深度检修/生成新技能/加入规则集）
- 生成记忆文本 → 写入 `semantic.db`
- 调用 `memory_palace.py bind` 绑定到档案室桩位

**绑定逻辑缺陷**：当前 hardcoded 全部绑定 `archive:2`，会覆盖已有绑定。需要改进为找空闲桩。

### 关键坑点

- `state.db` 的 messages 表时间字段是 `timestamp`（Unix float），不是 `created_at`
- `trigger_log.json` 格式：`ts` 字段（ISO8601），旧格式用 `timestamp`，兼容处理已内置
- `memories.tokens` 是 **NOT NULL**，写入时必须提供字符串类型的 token 数量
- dojo 沉淀绑定目前 hardcoded `archive:2`，多记忆会互相覆盖（待修复）

## 已注册 Cron

```
memory-palace-daily   09:00  随机漫步2个房间
memory-palace-autobind */4h   自动绑定高频触发记忆（>=2次/48h）
daily-distill         04:00  蒸馏昨日sessions→daily_distill/
```

## 扩展房间

如需新房间，在 `palace_map.json` 中添加：

```python
"新的房间ID": {
    "name": "显示名",
    "description": "描述",
    "loci_count": 5,
    "type": "skill",
    "loci": [
        {"id": "新房间_loci_1", "position": 1, "name": "桩位名", "bound_memory_id": null, "last_triggered": null},
        ...
    ]
}
```
