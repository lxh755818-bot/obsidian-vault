---
name: android-termux-python-packages
description: Installing Python packages with native extensions on Android Termux (Python 3.13, AArch64). Workaround strategies when pip/pypi wheels fail to build.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [android, termux, python, installation, troubleshooting]
    related_skills: [termux-api]
---

# Android Termux Python 包安装

在 Android Termux (Python 3.13, AArch64) 环境下安装带原生扩展的 Python 包时的特殊处理。

## 已知问题

### wandb (weights & biases)
- **问题**: 源码编译需要 `go` 二进制来构建 wandb-core Go 模块
- **解法**: `pip install wandb --only-binary=:all:` 或者安装旧版 wheel  
  `pip install wandb==0.21.0` (有预编译 wheel)

### pandas / numpy
- **问题**: Python 3.13 on Android aarch64 — PyPI 上没有 cp313 aarch64 android 的二进制 wheel。`pip install pandas --only-binary=:all:` 失败，tsinghua mirror 和 pypi.org 均无此平台的 wheel。
- **影响**: baostock, yfinance, akshare, stock-mcp 等均依赖 pandas，无法直接运行
- **解法 A (HTTP API 绕过)**: 直接调数据源的 HTTP API（不需要 pandas），用标准库 json + requests 解析，指标计算自己写纯 Python 版。东方财富 push2his.eastmoney.com API 可获取 A股 K线/行情/板块数据，已验证可用。
- **解法 B (Docker 远端部署)**: 在有 Docker 的机器上跑 stock-mcp，Termux 做调用端（通过 MCP over HTTP）
- **注意**: numpy 2.4.3 在 hermes-agent venv 里已经装好（纯 Python wheel），但 pandas 无解

### tinker (Python 客户端)
- **问题**: 手动复制源码后 `_version.py` 用 `importlib.metadata.version()` 查不到包元数据
- **解法**: 手动写入版本文件  
  ```python
  # /path/to/venv/lib/python3.13/site-packages/tinker/_version.py
  __title__ = "tinker"
  __version__ = "1.0.0"
  ```

### torch (PyTorch)
- **问题**: PyTorch 官方未发布 Android/AArch64 的 wheel，无法从 pip 安装，源码编译在 Termux 上极难成功
- **解法**: 此平台无法安装 torch，需要在 x86_64 + GPU 服务器上运行相关代码

### LanceDB (向量数据库)
- **问题**: `pip install lancedb` 失败 — 依赖 `pylance` 不存在于 PyPI（包名与 VSCode Python Language Server 冲突）；`pip install lance` 安装的是另一个图像处理库（PyPI 包名冲突）
- **解法**: 换用轻量替代方案（见下方"Android Termux 向量语义记忆方案"）

### sentence-transformers / faiss-cpu
- **问题**: Python 3.13 + Android aarch64 无预编译 wheel，源码编译需要 LAPACK/BLAS 线性代数库
- **解法**: 不在 Termux 上跑本地 embedding 模型

### sqlite-vss
- **问题**: `sqlean.py` 包装器是 Linux x86_64 专用（.so 文件），Android 不兼容；Termux 自带 SQLite 虽有 JSON1 扩展但无法加载外部 .so
- **状态**: 不可用

## Android Termux 向量语义记忆方案

在 Termux 上无法安装主流向量数据库（LanceDB/faiss/chromadb），推荐以下替代方案：

### 方案 A：MiniMax Embedding API + SQLite（✅ 推荐）
- 用 MiniMax `embo-01` API 做 embedding（无本地模型依赖）
- 用 SQLite 存向量（纯 Python，无原生扩展）
- 距离计算：NumPy 或纯 Python 手写余弦相似度
- 依赖：`pip install numpy`（venv 里有）+ 标准库 `sqlite3`
- 验证状态：代码已写好（`~/simple_mem_lite.py`），待 MiniMax API Key 测试

### 方案 B：关键词 + SQLite（✅ 最简）
- 不用向量 embedding，用 TF-IDF 或关键词匹配
- 适合记忆系统（精确匹配 > 语义相似）
- 依赖：仅标准库 `sqlite3`

### 方案 C：Docker 远端
- 在有 Docker 的 x86_64 机器上跑 LanceDB/Chromadb，Termux 做调用端

## 通用技巧

1. **始终先试 pkg 管理器**: `pkg install -y python-<package>`
2. **手动复制**: 如果 pkg 装了但 venv 里没有，直接 cp 目录和 dist-info
3. **使用 --prefer-binary / --only-binary**: 避免源码编译
4. **配置国内镜像加速**:  
   `pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple`
5. **Submodule 初始化**:  
   `git submodule update --init <path>`
6. **后台运行长任务**: pip install 超时用 `background=true` + `notify_on_complete=true`，然后 `process` 查询状态

## 验证已安装的包

```bash
pip list | grep <package>
python3 -c "import <package>; print(<package>.__version__)"
```
