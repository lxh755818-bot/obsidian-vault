---
name: obsidian
description: Obsidian 笔记工具 — 本地 Markdown 知识库。作为小a 的知识沉淀层，与 Hermes 实时记忆层配合使用。
trigger: 用户想建知识库 / 需要沉淀 learnings / 调研笔记工具 / 想知道 Obsidian 怎么用
category: note-taking
owner: 小a
---

# Obsidian — 知识沉淀层

## 定位：第二大脑，不是实时记忆

```
Hermes 实时记忆（小a 自己用，毫秒级）
    ↓ distill（每次 Ralph 迭代后自动写入）
Obsidian 知识库（小a 和刘小豪 都能看）
```

- **Obsidian = 人类可读的知识图书馆**，时间越久越值钱
- **Hermes LCM/fact_store = AI 实时记忆**，快速检索
- 两者互补，不竞争

## 核心判断

| 工具 | 适合场景 | 手机端 |
|------|----------|--------|
| **Obsidian** | 桌面端为主、知识图谱、本地私有 | 一般（桌面端碾压） |
| **Logseq** | 移动端为主、outline 风格 | 稍好但 Android 不稳 |
| **Notion** | 协作、团队、手机端最佳 | 碾压级 |

**刘小豪用电脑为主 → Obsidian 桌面端** ✅ 已确认

## Vault 位置

**Android Obsidian vault（当前唯一 vault）：**
```
/storage/emulated/0/Documents/xiaoack/小a/
```

> ⚠️ 不在 Termux 目录下！这是 Android 共享存储，git init 时需注意 safe.directory 配置。

## 目录结构（已落实）

```
/storage/emulated/0/Documents/xiaoack/小a/   ← Android vault，独立 git 仓库
├── .obsidian/                # Obsidian 配置（勿 git add）
├── 00-关于本库.md             # vault 说明
├── daily/                    # 每日 distillation 报告
│   └── 2026-04-30.md
├── learnings/                # Ralph 迭代 learnings 归档
│   ├── 小a进化记录.md        # 重大错误复盘
│   └── README.md
├── projects/                # 项目笔记
│   └── 项目模板.md
└── system/                   # 小a 自我认知、进化系统
    ├── 小a进化系统.md         # 完整进化架构文档
    └── 小a-自我认知.md

.gitignore（已配置）:
  .obsidian/workspace-mobile.json
  .obsidian/graph.json
  未命名.base
```

### 环境变量

```bash
OBSIDIAN_VAULT_PATH=/storage/emulated/0/Documents/xiaoack/小a
```

## 同步脚本（已落实）

```bash
bash /data/data/com.termux/files/home/.hermes/scripts/obsidian_vault_sync.sh
```

**输出示例**：
```
[sync] ✅ Pushed successfully
```

**脚本规范（2026-04-30 更新）**：
- Android vault push 到 GitHub 时，`master` → `main` 分支映射
- 使用 HTTPS + token 内嵌 remote URL（`origin https://lxh755818-bot:{TOKEN}@github.com/...`）
- GitHub token：classic PAT + `repo` scope（Fine-grained PAT 会 403）

---

## Wikilinks 规范（2026-04-30 建立）

**每写一篇笔记，必须在末尾加「关联笔记」章节**，织入双向链接：

```markdown
## 关联笔记

- [[小a进化系统]] — 完整进化架构
- [[小a进化记录]] — 历史错误复盘
- [[2026-04-30]] — 今日工作
- [[00-关于本库]] — 本库说明
```

**好处**：
- Obsidian 图谱（Graph View）里节点会自动连线
- 快速跳转相关笔记
- 知识网络随时间自然生长

**命名规范**：
- 中文文件名直接用：`[[小a进化系统]]`
- 日期笔记用：`[[2026-04-30]]`（YYYY-MM-DD 格式）

---

## GitHub 同步状态（2026-04-30 实测完成）

- ✅ Android vault git 已初始化（root commit: `486a4c2`）
- ✅ GitHub remote 已配置（HTTPS URL + token 内嵌）
- ✅ GitHub 仓库已创建（lxh755818-bot/obsidian-vault）
- ✅ 仓库分支：`master`（Android 端）→ `main`（GitHub 端），rebase 后推送
- ✅ Token：classic PAT + `repo` scope，已验证可写
- ✅ sync 脚本已就绪：`~/.hermes/scripts/obsidian_vault_sync.sh`

**Token scope 问题已解决（2026-04-30）：**
- Fine-grained PAT 只有读权限，所有写操作 403
- 换成 classic PAT + `repo` scope 后 push 成功
- 参考：`references/vault-setup.md` 详细排查流程

详见 `references/vault-structure.md`

### 环境变量

```bash
OBSIDIAN_VAULT_PATH=/storage/emulated/0/Documents/xiaoack/小a
```

### 写入笔记

```bash
VAULT="${OBSIDIAN_VAULT_PATH}"
cat > "$VAULT/Note Name.md" << 'ENDNOTE'
# Title

Content
ENDNOTE
```

### 追加到笔记

```bash
VAULT="${OBSIDIAN_VAULT_PATH}"
echo -e "\nNew content." >> "$VAULT/Existing Note.md"
```

### 搜索

```bash
VAULT="${OBSIDIAN_VAULT_PATH}"

# 按文件名
find "$VAULT" -name "*.md" -iname "*keyword*"

# 按内容
grep -rli "keyword" "$VAULT" --include="*.md"
```

### 列出所有笔记

```bash
VAULT="${OBSIDIAN_VAULT_PATH}"
find "$VAULT" -name "*.md" -type f
```

## Wikilinks

Obsidian 双向链接语法：

```markdown
[[Note Name]]           # 链接到某笔记
[[Note Name#Heading]]   # 链接到某笔记的特定章节
![[Note Name]]          # 嵌入（embed）某笔记内容
```

## Obsidian AI 插件（桌面端）

推荐插件（2026）：

| 插件 | 功能 |
|------|------|
| **Smart Connections** | 语义搜索笔记内容 |
| **Copilot** | 对话式 AI，搜索+生成 |
| **Text Generator** | 根据模板生成内容 |

安装：Obsidian Settings → Community Plugins → 搜索插件名

## References

- `references/obsidian-vs-alternatives.md` — Obsidian/Notion/Logseq/Capacities 对比决策指南
- `references/vault-structure.md` — vault 目录结构 + 模板 + 写入接口代码
- `references/vault-setup.md` — GitHub sync 配置、token scope 问题、distill_learnings 集成（2026-04-30 实测）
