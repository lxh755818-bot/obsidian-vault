---
name: feishu-image-workflow
description: 飞书图片工作流 — 接收、WebP格式转换、图像理解、发送完整链路。解决飞书图片扩展名为.jpg实际为WebP的工具链断裂问题。
category: messaging
tags: [feishu, image, webp, vision, conversion]
version: 1.0.0
created: 2026-05-04
triggers:
  - 用户发送图片/截图到飞书对话
  - 需要分析图片内容（配置单、文档、照片等）
  - 图片理解工具报错"没有看到图片"或格式错误
---

# 飞书图片工作流

## 核心问题

飞书传输图片时使用 **WebP 格式**，但文件扩展名强制标记为 `.jpg`。导致：
- 图片理解工具（vision_analyze、mcp_minimax_understand_image）读取文件头时发现是 WebP 而拒绝处理
- `execute_code` 的 PIL 库缺失，无法直接处理
- 需手动转换格式后才能分析

## 标准处理流程

### Step 1 — 检查文件格式

飞书图片会缓存到 Termux 路径：
```
/data/data/com.termux/files/home/.hermes/cache/images/img_<hash>.jpg
```

用 Python 检查文件头魔数：

```python
with open(img_path, 'rb') as f:
    header = f.read(10)
if header[:4] == b'RIFF' and b'WEBP' in header:
    print("Format: WebP - needs conversion")
elif header[:2] == b'\xff\xd8':
    print("Format: JPEG - can use directly")
```

### Step 2 — WebP → PNG → JPEG 转换

```bash
# 路径定义
IMG_PATH="/data/data/com.termux/files/home/.hermes/cache/images/img_<hash>.jpg"
HOME="/data/data/com.termux/files/home"
PNG_OUT="$HOME/img_convert.png"
JPG_OUT="$HOME/img_convert.jpg"

# Step A: dwebp 解码 WebP → PNG
dwebp "$IMG_PATH" -o "$PNG_OUT" 2>&1

# Step B: ffmpeg 转换 PNG → JPEG
ffmpeg -y -i "$PNG_OUT" "$JPG_OUT" 2>&1 | tail -5
```

**关键工具**：
- `dwebp` — 来自 `libwebp` 包，已预装在 Termux
- `ffmpeg` — 已预装，支持 pipe 模式

### Step 3 — 图像理解

转换后 JPEG 可直接用于所有图片理解工具：

```python
mcp_minimax_understand_image(
    image_source="/data/data/com.termux/files/home/img_convert.jpg",
    prompt="详细描述这张图片中的所有文字和配置信息..."
)
```

### Step 4 — 发送图片（可选）

如果需要把分析结果图片发回飞书，参考 `feishu-send-image` skill。

---

## 常见坑点

### ❌ 不要做的事

- **不要**直接用 `.jpg` 路径传给 vision_analyze — 文件仍是 WebP
- **不要**尝试用 PIL 处理 — Termux 环境没有 Pillow
- **不要**用 `file` 命令检查格式 — Termux 的 file 命令缺失

### ✅ 验证步骤

转换后用 Python 检查 JPEG 魔术字节确认成功：

```python
with open(jpg_out, 'rb') as f:
    header = f.read(2)
assert header == b'\xff\xd8', "Not a valid JPEG"
```

---

## 快速命令（单行）

```bash
# 完整转换一行流
dwebp /data/data/com.termux/files/home/.hermes/cache/images/img_<HASH>.jpg -o /tmp/a.png && ffmpeg -y -i /tmp/a.png /tmp/a.jpg 2>/dev/null && echo "OK"
```

---

## 相关 Skills

- `feishu-send-image` — 图片发送（发送方视角）
- `mcp` — MCP 工具配置（image understanding 工具列表）
- `minimax-image-generation` — 图片生成（text→image，与本技能互补）

---

## 更新日志

- v1.0.0 (2026-05-04): 初始化，解决飞书 WebP 图片无法分析的问题
