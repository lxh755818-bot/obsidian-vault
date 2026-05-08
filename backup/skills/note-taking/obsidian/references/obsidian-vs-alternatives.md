# Obsidian vs Alternatives — Decision Guide

> Last updated: 2026-04-30

## 核心判断

| 工具 | 适合场景 | 不适合场景 |
|------|----------|------------|
| **Obsidian** | 桌面端为主、知识图谱、私有本地 | 手机端体验一般 |
| **Logseq** | 移动端为主、outline 风格 | Android 端评价两极 |
| **Notion** | 协作、团队、手机端最佳 | 数据在云、不算"自己拥有" |
| **Capacities** | 结构化对象、Notion 替代 | 要付费、生态新 |

## 小a 的使用场景

**Obsidian = 知识沉淀层（不是实时记忆层）**

```
Hermes 实时记忆（小a 自己用）
    ↓ distill（每日蒸馏）
Obsidian 知识库（我和小a 都能看）
```

- **Hermes LCM/fact_store** → 毫秒级实时检索，AI 自己用
- **Obsidian** → 人类可读、跨工具、统一格式，长期积累

## Obsidian 桌面端优势（2026）

- 插件生态 3000+，AI 插件（Copilot/Smart Connections）成熟
- Canvas 图谱可视化
- 本地 Markdown 文件，Git 管理版本
- 完全免费（本地使用）

## Notion 桌面/移动端优势

- 手机端体验碾压级
- API 写入已有 skill（`notion` skill 已存在）
- 实时协作

## 选择建议

- **你用电脑为主** → Obsidian 桌面端， vault 放本地或 Git 同步
- **想要手机也能看** → Notion（手机端最强），小a 用 API 写
- **两者都要** → Obsidian 桌面端为主 + Notion 手机辅助

## Vault 位置

当前：`/data/data/com.termux/files/home/obsidian-vault/`（空的，2026-04-26 创建）
