# Source: `daily-distill`

---
name: daily-distill
description: 每日蒸馏技能 — 从 Hermes state.db 提取过去24小时会话，生成每日摘要。过滤SYSTEM消息/Cron心跳，输出可读日报，存储到 daily_distill/。
category: system
tags: [memory, distillation, session, daily, archive]
trigger: [每日蒸馏, sessions摘要, 日报生成, distill]
dependencies: []
---

# 每日蒸馏 (Daily Distill)

## 核心功能

从 `~/.hermes/state.db` 提取过去24小时会话消息，生成结构化每日摘要，写入 `~/.hermes/memory/daily_distill/YYYY-MM-DD.md`。

**每天只蒸馏一次**（防重复），04:00 自动执行。

## 执行方式

```bash
# 标准执行
python ~/.hermes/scripts/daily_distill.py

# 预览（不写入文件）
python ~/.hermes/scripts/daily_distill.py --dry-run

# 指定日期
python ~/.hermes/scripts/daily_distill.py --day 2026-04-25
```

## 输出格式

```markdown
# 每日蒸馏 — 2026-04-26
生成时间: 2026-04-26T04:00:12
消息总数: 993
关键消息: 152

## 关键交互
1. 👤 用户消息摘要...
2. 🤖 助手消息摘要...

## 决策记录
- 决策类消息（包含"已修复"/"已配置"/"决定"等）

## 技术笔记
- 包含技术内容的代码/API/skill相关消息
```

## 关键过滤规则

**跳过（内置，无需配置）**：
- `[SYSTEM:` 消息
- `DELIVERY:` 消息
- `Cron job ... completed`
- `EvoMap heartbeat OK`
- `HERMES DOJO 日报`
- 短于10字符的消息
- 纯标点/空白消息

## 已知坑点

### state.db schema（必须知道）

```python
# messages 表时间字段是 timestamp（Unix float），不是 created_at
timestamp: REAL  # Unix epoch float，例: 1776358325.7080996
# ❌ 错误：WHERE created_at >= cutoff_iso
# ✅ 正确：WHERE timestamp >= cutoff_ts
cutoff_ts = datetime.now().timestamp() - hours * 3600
```

### 消息 content 可能是 JSON 字符串

```python
# content 字段可能是 str 或 list，需要兼容处理
if isinstance(d.get("content"), str):
    try:
        d["content"] = json.loads(d["content"])
    except:
        pass
```

### 活跃 sessions 数量

- state.db 有 ~722 sessions，~16888 messages
- 每次查询限制50个最新 session，避免全表扫描
- 时间窗口：24小时

## Cron 注册

```
daily-distill  job_id: 605c6119c321
执行时间: 每天 04:00
脚本: ~/.hermes/scripts/daily_distill.py
输出: ~/.hermes/memory/daily_distill/YYYY-MM-DD.md
防重: 已蒸馏的日期自动跳过
```

## 与记忆宫殿的关系

```
daily_distill/*.md（每日摘要）
    ↓ 可被 memory_palace 引用
    ↓ 或手动整理后 add_memory 到 semantic.db
```

蒸馏后的人工整理流程：
1. 读 `daily_distill/YYYY-MM-DD.md`
2. 识别关键决策和技术笔记
3. 用 `memory_palace.py add` 写入 semantic.db
4. 高频访问的记忆 → auto-bind 到宫殿桩位
