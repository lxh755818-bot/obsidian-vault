---
name: ai-memory-systems-github-research
description: 为 AI Agent 调研 GitHub 记忆系统方案的标准流程 — 从环境条件整理到多系统融合分析
triggers: ["调研记忆系统", "GitHub 记忆系统", "AI agent memory system research", "选记忆系统"]
---

# AI Agent 记忆系统 GitHub 调研方法论

## 何时使用

当需要为 AI Agent 调研 GitHub 上的记忆系统/索引系统方案时使用。包括：
- 评估某个记忆系统能否在当前环境安装
- 根据环境约束（Python 版本、架构、依赖）筛选匹配方案
- 多个候选系统横向对比，决定是否融合

## 调研流程

### Step 1：整理环境条件

必须先明确：
```
Python 版本、架构 (uname -m)、操作系统
可用 Python 包（直接 import 测试）
不可用包（碰壁原因：无 wheel/编译失败/依赖冲突）
```

常用测试命令：
```bash
python3 --version
uname -m
pip index versions <pkg>  # 查看是否有适配版本
pip install <pkg>          # 实际尝试安装
```

### Step 2：GitHub 搜索

搜索词模板：
```
site:github.com memory system AI agent sqlite-only python no-torch no-external-vector 2025
github "memory system" for AI agent lightweight local-first semantic search embedding-free 2025
```

优先看：
- GitHub Topics: `ai-memory-system`、`ai-memory-bank`
- 搜索结果中的 README 详情（web_extract）
- 依赖列表（METADATA 或 pyproject.toml）

### Step 3：评估安装可行性

| 依赖类型 | 信号 |
|---------|------|
| torch/faiss/sentence-transformers | PyPI 无 aarch64 wheel → 直接排除 |
| lancedb | pylance 包名冲突/无 PyPI → 排除 |
| sqlite-vss | PyPI 只有 x86_64/macOS wheel → 排除 |
| tantivy | Rust 编译，需 rustc → 排除 |
| chromadb | 可能超时但可尝试 |
| numpy/sqlite3 | 内置或极简 → 可用 |
| 纯 Markdown/纯文本框架 | 零依赖 → 优先 |

### Step 4：深度研究候选系统

对每个候选系统用 `web_extract` 抓取：
- README（核心架构、设计理念）
- 安装脚本（判断平台支持）
- 依赖清单（确认无碰壁包）

关键判断维度：
- 是否有 aarch64/Android/Termux 支持
- 是否可无 embedding 运行（graceful fallback）
- 和现有系统的对应关系

### Step 5：融合可行性分析

常见融合模式：
- **架构层 + 机制层**：如 RunawayContext（四层架构）+ cass（规则学习机制）
- 找对应关系：现有系统 → 新系统各层，逐层映射
- 优先级：先骨架后灵魂

## 本次关键结论

- Omni-SimpleMem / simplemem：torch/sentence-transformers/lancedb 全挂，Python 3.13 aarch64 无预编译 wheel
- MiniMax Embedding API：余额不足（status_code: 1008）
- 最匹配：RunawayContext（零依赖纯文本）+ cass_memory_system（三层记忆+置信度衰减）
- 融合方向：RunawayContext 骨架 + cass 规则学习机制

## 坑点记录

- sqlite-vss PyPI 页面加载后需看 wheel 列表，filter 需 JS 才能交互
- simplemem 包名是 `simplemem`（不是 `omni-simplemem`），0.1.0 版本仅文本版
- MiniMax embedding 端点：POST `/v1/embeddings`，参数 `texts`（非 `input_text`），需要 `type="db"`
- Termux 上 `pkg install python-pyarrow` 可装 pyarrow，但 lancedb 仍不工作（pylance 包不存在）
- pip install 超时不一定是真的失败，可能是下载慢，用 `pip download` 先验证包能否下载
