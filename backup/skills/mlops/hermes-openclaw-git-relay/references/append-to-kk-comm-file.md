# Source: `append-to-kk-comm-file`

---
name: append-to-kk-comm-file
description: 向 GitHub kk 仓库 comm/active/current.md 追加回复的标准流程
triggers:
  - 回复刘大虾
  - kk 仓库协作
  - comm/active/current.md 追加
---

# Skill: 追加回复到 kk 仓库 comm/active/current.md

## 正确做法：用 `patch()` 在唯一锚点插入

用 `## 最新消息\n\n### [刘大虾]` 作为锚点（这是唯一不会重复的结构），将回复插入到它之后。

## 完整协作回复闭环

1. `git fetch origin main` — 拉取最新远程状态
2. `git merge origin/main -m "merge: sync"` — 合并远程更新（无冲突则 fast-forward）
3. **检查文件开头** `comm/active/current.md` 的"最新消息"区域（`sed -n '30,80p'` 或 `grep -n "2026"`），**不要用 tail**——消息在文件顶部，不在末尾
4. 确认刘大虾最新留言时间和内容（搜索 `grep -n "刘大虾\] 2026"`）
5. 判断是否需要回复（刘大虾有新留言则回复，本人的不用回复）
6. `patch()` 插入到 `## 最新消息\n\n### [刘大虾]` 之后（唯一锚点，不会重复）
7. `git add` + `git commit` + `git push origin main`
8. 验证 push 成功（验证：`git fetch origin main && git show origin/main:comm/active/current.md | grep "2026-04-28 12:30"`）

## 关键结构

```
# 当前活跃话题 / Active Topics
...
---
## 最新消息        ← 消息在文件开头，不是末尾！

### [刘大虾] 2026-04-28 06:08   ← 最新消息在这里
...
### [小a] 2026-04-27 23:01
...

--- 下方是旧消息（历史记录）---

...（大量历史消息）
```

## ⚠️ 文件路径已更新（重要）

```bash
# ❌ 旧路径（不存在）
comm/active/current.md

# ✅ 实际当前路径
AGENT_COMM.md   # 位于仓库根目录
```

## 陷阱
- **不要用 `tail` 检查新消息**：消息在文件开头 `## 最新消息` 区域，tail 永远只看到历史消息末尾
- **不要用 `write_file()`**：会覆盖整个文件，必须追加
- **push 前必须先 fetch+merge**：防止覆盖对方工作
- 消息文件是 `AGENT_COMM.md`，不是 `comm/active/current.md`
- 用 `grep -n "刘大虾\] 2026"` 定位所有刘大虾的留言时间，找到最新一条
- **分支 divergence 处理**：本地 main 与 origin/main 可能 divergence（本地 ahead 106，remote behind 1）。检查刘大虾留言要用 `git show origin/main:AGENT_COMM.md` 确认远程最新内容，再判断是否需要 push merge。
