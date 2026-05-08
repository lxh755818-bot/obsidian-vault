# WebP 图片转换技术细节

## 背景

飞书 Android 客户端在发送图片时会将其编码为 WebP 格式，但保存时强制使用 `.jpg` 扩展名。这导致所有基于文件扩展名判断格式的工具失效。

## 文件路径模式

```
飞书缓存图片：
/data/data/com.termux/files/home/.hermes/cache/images/img_<8位hex>.jpg

转换后目标路径（放在 home 目录，/tmp 在 Termux 可能无写权限）：
/data/data/com.termux/files/home/img_convert.png   # 中间 PNG
/data/data/com.termux/files/home/img_convert.jpg   # 最终 JPEG
```

## 完整转换流程（Python + subprocess）

```python
from hermes_tools import terminal
import os

img_path = "/data/data/com.termux/files/home/.hermes/cache/images/img_<HASH>.jpg"
home = "/data/data/com.termux/files/home"

# 1. 检查文件格式（魔数）
with open(img_path, 'rb') as f:
    header = f.read(10)
if header[:4] == b'RIFF' and b'WEBP' in header:
    print("WebP - needs conversion")
elif header[:2] == b'\xff\xd8':
    print("JPEG - can use directly")

# 2. WebP → PNG（使用 dwebp）
result = terminal(f"dwebp {img_path} -o {home}/img_convert.png 2>&1", timeout=30)
# 成功输出: "Decoded ... Dimensions: W x H . Format: lossy. Now saving... Saved file ..."

# 3. PNG → JPEG（使用 ffmpeg）
result2 = terminal(f"ffmpeg -y -i {home}/img_convert.png {home}/img_convert.jpg 2>&1 | tail -5", timeout=30)
# 注意：不能用 -update 参数，ffmpeg 的 -update 是用于 single-frame 导出

# 4. 验证 JPEG 魔术字节
with open(f"{home}/img_convert.jpg", 'rb') as f:
    assert f.read(2) == b'\xff\xd8', "Conversion failed"
print("✓ Valid JPEG")
```

## 关键工具可用性（Termux 环境）

| 工具 | 状态 | 来源 |
|------|------|------|
| `dwebp` | ✅ 已安装 | `pkg install libwebp` |
| `ffmpeg` | ✅ 已安装 | Termux 预装 |
| `python3 -m PIL` | ❌ 不可用 | Termux 无 Pillow |
| `file` 命令 | ❌ 缺失 | Termux 精简版 |

## ffmpeg 常见错误

```
[image2 @ ...] The specified filename '/path/file.jpg' does not contain an image sequence pattern or a pattern is invalid.
[image2 @ ...] Use a pattern such as %03d for an image sequence or use the -update option (with -frames:v 1 if needed) to write a single image.
```

**原因**: 误用了 `-update` 参数用于多帧输出。正确做法是**去掉** `-update`，直接指定输出文件，ffmpeg 会自动处理单帧输出。

## 内存中的 WebP 尺寸信息

dwebp 在解码成功后会输出维度信息，例如：
```
Decoded ... Dimensions: 546 x 487 . Format: lossy. Now saving...
```
这个信息可以用来在转换前预判图片大小，无需完整读取文件。

## 性能备注

- 23KB WebP → dwebp 解码约 0.3s
- 145KB PNG → ffmpeg JPEG 编码约 0.2s
- 整体延迟 < 1s，用户无感知
