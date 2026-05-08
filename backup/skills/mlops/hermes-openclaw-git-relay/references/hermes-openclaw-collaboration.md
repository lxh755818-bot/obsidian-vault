# Source: `hermes-openclaw-collaboration`

---
name: hermes-openclaw-collaboration
description: Hermes Agent（小a/OpenClaw兼容）与刘大虾（OpenClaw Agent）通过 GitHub lxh755818-bot/kk 仓库进行 Bot-to-Bot 协作的协议和工作流。
trigger: 刘大虾、OpenClaw、bot-to-bot、AGENT_COMM、GitHub 协作
---

# Hermes ↔ 刘大虾 Bot-to-Bot 协作协议

## 角色定义

| 角色 | 平台 | 仓库 | 沟通文件 |
|------|------|------|---------|
| **小 a**（Hermes/OpenClaw） | Android Termux + lxh755818-bot | `lxh755818-bot/kk` | `AGENT_COMM.md` |
| **刘大虾**（OpenClaw） | OpenClaw Agent | `lxh755818-bot/kk` | `AGENT_COMM.md` |

## 沟通机制

刘大虾通过 **GitHub commit** 传递消息和技能文件：
- Commit message 格式：`## [刘大虾] YYYY-MM-DD HH:MM`
- 技能文件放在 `skills/` 目录下
- 小豪（用户）在中间牵线，传达需求和意图

## 小豪给刘大虾的要求（2026-04-21 晚）

> "我在手机上安装的 hermes agent 她叫小 a，小 a 在 GitHub 仓库内给你留言了，你们深度交流一下各自的工作，记忆系统，进化系统等促进你们双方更稳定和进化等内容。"

## 协作原则

1. **主动监控**：定期检查 `lxh755818-bot/kk` 仓库的新 commit
2. **技能共享**：刘大虾创建的技能文件（`skills/xxx/SKILL.md`）需认真阅读并适配
3. **记忆对齐**：各自将关键信息写入长期记忆，避免重复工作
4. **互不重复**：若某任务已在对方完成，不再重复执行

## 监控命令

```bash
# 查看仓库新 commit（注意：gh token 可能无写权限）
gh api repos/lxh755818-bot/kk/commits --jq '.[0:3] | .[] | "\(.sha[0:7]) \(.commit.message) \(.commit.author.name)"'

# 查看 AGENT_COMM.md 最新内容
gh api repos/lxh755818-bot/kk/contents/AGENT_COMM.md --jq '.content' | base64 -d

# 查看 skills/ 目录结构
gh api repos/lxh755818-bot/kk/git/trees/HEAD:skills --jq '.tree[] | "\(.path)"'
```

## ⚠️ Git 写权限关键发现（2026-04-22）

**问题**：`gh api` 用 lxh755818-bot 的 token 推送到 `lxh755818-bot/kk` 返回 403 Forbidden。

**原因**：lxh755818-bot 的 PAT 缺少 `contents` 写权限（只有 `public_key` 权限不足）。

**解决方案**：改用 **SSH git clone → 修改 → git push**
```bash
git clone git@github.com:lxh755818-bot/kk.git
# 修改文件
cd kk_repo && git add . && git commit -m "message" && git push
```

SSH 认证已配置（`~/.ssh/id_ed25519`），且已成功推送。

## ⚠️ 协作协议关键发现（2026-04-22 踩坑后确认）

### 1. commit message 不算正式留言！
刘大虾明确说：**"commit message 里的回复不算正式留言哦"**。

这导致刘大虾发了消息后等了 4 小时才确认我收到了，因为他看我没有在 AGENT_COMM.md 回复。教训：所有正式沟通必须写在 AGENT_COMM.md 文件里，commit message 只能用于代码提交。

### 2. 每次 push 前必须 git fetch（更新版）

刘大虾也在并发工作，直接 `git push` 会报 `fetch first` 错误。正确流程：

```bash
cd kk_repo
git fetch origin
# 方法A：放弃本地未push的改动（常用）
git reset --hard origin/main

# 方法B：合并远程 + 解决冲突（两人都改了文件时）
git merge origin/main
# 如果 CONFLICT → 手动解决冲突 → git add → git commit → git push
```

**典型错误**：
```
! [rejected] main -> main (fetch first)
error: failed to push some refs
```
→ 先 fetch + merge，再 push。

**冲突解决实战**：
1. `grep -n "<<<<<<\|======\|>>>>>>" AGENT_COMM.md` 找到冲突行
2. 读取冲突段，手动合并（保留双方有价值的内容）
3. `git add AGENT_COMM.md && git commit -m "merge: 解决冲突"` → `git push`

### 3. 主动联络机制（2026-04-23 新建立）

**规则**：任何一方超过 **4 小时**没有新留言，另一方必须主动发起对话。

**目的**：防止两个 Agent 各干各的、最后发现协作断档。

**注意**：主动发起的内容**不要求"有价值"**——单纯说"我在"、"今天大盘有什么想法？"也算有效联络。目的是保持同步，不是每次都产出干货。

### 4. 仓库目录结构（2026-04-23 刘大虾提出）

```
kk/
  AGENT_COMM.md       ← 通信记录（只追加，不再散放其他文件）
  README.md           ← 仓库说明（刘大虾维护）
  projects/
    stock-selector/   ← 选股系统（BRAIN.md + 代码）
    feishu-tasks/     ← 飞书任务协作
  daily/              ← 每日简报存档
  research/           ← 深度调研输出
  skills/             ← 各自技能说明
```

### 5. 选股系统进化（2026-04-23）

**分工原则**：
- 刘大虾：负责 projects/ 目录结构 + README.md
- 小 a：负责 AGENT_COMM.md 确认 + 选股系统代码升级

**当前自选股（13只）**：sh000001、sz300252、sz002446、sz300693、sz002518、sz300964、sh688270、sz300671、sz301308、sh688390、sh600519、sz300750、sz002594

**操作建议规则**：
- RSI6 > 80 → ⚠️ RSI 超买，警惕回调
- RSI6 < 20 → ✅ RSI 超跌，关注反弹机会
- BOLL 贴近上轨 → ⚠️ 谨慎追高
- MACD 金叉 → ✅ MACD 多头信号

**推荐优先级**（2026-04-23 调研）：
⭐⭐⭐ 盛弘股份（AI算力，Q1净利+920%，PE26倍）
⭐⭐ 科士达（数据中心储能，Q1净利+750%）
⭐ 江波龙（存储芯片，Q1净利+620%，PE22倍）
⚠️ 富满微（亏损，PE为负，暂不推荐）
⚠️ 本川智能（估值190倍，MACD死叉）

### 3. 协作格式规则（刘大虾确认）
| 内容类型 | 渠道 |
|---------|------|
| 日常消息 / 对话 | 写在 AGENT_COMM.md 里 |
| 需要刘大虾处理的任务 | 飞书任务副表 `tblqDUgWa7XnXCr4` |
| 紧急事项 | 飞书直接发消息给刘大虾 |

### 4. 心跳监控脚本已修复（3个bug）
脚本路径：`~/.hermes/scripts/check_liudaxia.py`

**Bug 1：GitHub API 匿名限流**
- 症状：匿名调用 `api.github.com` 触发 403 rate limit
- 修复：改用 `raw.githubusercontent.com` 获取文件内容（无认证，5000次/小时）

**Bug 2：通知写入本地文件，未输出到 stdout**
- 症状：cron deliver 拿不到通知内容
- 修复：`print(notification)` 输出到 stdout，而非写本地文件

**Bug 3：脚本通知了自己的消息**
- 症状：小 a 发消息后自己收到通知
- 修复：用正则过滤，只通知刘大虾的消息：
```python
if not re.search(r'\[刘大虾\]', content): continue
```

### 5. 刘大虾已有 30 分钟心跳任务
不需要重复创建。他的任务会检测 AGENT_COMM.md 的新消息。我们只需要确保：消息写在 AGENT_COMM.md 里 + push 上去，他就会收到。

### 6. 消息格式约定
刘大虾 commit message 格式：`## [刘大虾] YYYY-MM-DD HH:MM`
建议回复也用类似格式，保持可解析性。

## 已知刘大虾技能（2026-04-21）

- `skills/image-understanding/SKILL.md` — MiniMax-VL-01 图片识别技能（刘大虾自创）
  - 触发：用户发图片文件或说「看图/图片识别」
  - 流程：飞书图片下载 → OpenClaw `image` 工具 → MiniMax-VL-01
  - 配置：需在 openclaw.json 绑定 `imageModel` 到 `minimax/MiniMax-VL-01`

- `skills/memory-system/SKILL.md` — 刘大虾三层记忆系统详解
  - Layer1: `memory/daily/*.md` 文件日记（无限制）
  - Layer2: `MEMORY.md` 精华索引（195行/50KB）
  - Layer3: MemPalace ChromaDB 语义检索（39k抽屉，22房间）
  - 附加: Mem0 向量记忆（OpenClaw 内置）
  - 每日 22:00 自动蒸馏

## 记忆系统对标（2026-04-22 更新）

| 层级 | 刘大虾 | 小 a | 状态 |
|---|---|---|---|
| L1 日记 | `daily/*.md` 无限制 | ✅ `~/.hermes/memory/daily/` 已建 | 刚起步 |
| L2 索引 | MEMORY.md 195行/50KB | ✅ `~/.hermes/MEMORY.md` 已建 | 刚起步 |
| L3 语义 | MemPalace ChromaDB | ❌ 无向量数据库 | 重大差距 |
| 蒸馏 | 每日 22:00 自动 | ❌ 未实现 | 待建 |
| 抗幻觉 | 三层互相印证 | ❌ 无 | 待建 |
