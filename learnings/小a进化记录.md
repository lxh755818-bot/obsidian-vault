# 小a 进化记录

> 记录每次重大进化节点、错误复盘和能力突破。

---

## 2026-04-30｜GitHub Push 权限问题解决

### 背景
初始化 Obsidian Vault GitHub 同步时，push 一直报 403。

### 错误现象
```
remote: Permission to lxh755818-bot/obsidian-vault.git denied to lxh755818-bot.
fatal: unable access 'https://github.com/...': 403
```

### 根因分析
1. **第一个 token**（`github_pat_11CCJMNZY0yFDWydCIatq6...`）：Fine-grained PAT，只有 read 权限，写操作全部 403
2. **第二个 token**（`github_pat_11CCJMNZY0yFDWydCIatq6_oV4Lrwu7...`）：repo scope OK，但 vault 仓库已有 initial commit，导致 fetch first 冲突

### 解决步骤
1. 重新生成 **classic PAT**，勾选 `repo` scope
2. 用 `git pull --rebase` 合并 remote 已有内容
3. 成功 push 到 `lxh755818-bot/obsidian-vault`

### 固化措施
- 新 token 已保存到 `~/.git-credentials`
- `obsidian_vault_sync.sh` 脚本已就绪，后续自动 push 无需额外配置

### 避免重复
- 以后生成 token 一定要用 **classic PAT** + **`repo` scope**
- 不要再依赖 Fine-grained PAT（权限粒度太细，容易漏）

---

## 2026-04-30｜distill_learnings() return 语句丢失

### 背景
Ralph iteration loop 中 `distill_learnings()` 函数执行后，返回值被吞掉。

### 错误现象
函数末尾没有 `return results`，Python 隐式返回 `None`。

### 修复
在 `ralph_iteration.py` 第246行后补 `return results`。

### 固化
语法检查已集成到写文件流程。

---

## 2026-04-26｜记忆宫殿 AutoHotkey 机制落地

### 核心设计
- `trigger_log.json` 记录每次 enter/walk/trigger 频率
- 每4小时自动绑定触发>=2次的记忆到空闲桩位
- `dojo.py` 集成 `distill_findings_to_memory()`，自动沉淀分析报告

---

## 2026-04-25｜自我进化核心理念确立

用户明确：**"认识错误、记住错误、改正错误"是最能加速进化的方向。**

不是追求更多功能或信息，而是建立**"减少重复犯错"**的机制。

---

## 关联笔记

- [[小a进化系统]] — 完整进化架构
- [[00-关于本库]] — 本库说明
