# Source: `mcp-image-understanding`

---
name: mcp-image-understanding
description: "使用 mcp_minimax_understand_image 分析本地图片，路径格式为 /data/data/com.termux/files/home/.hermes/cache/images/img_xxx.jpg。区分快速描述和详细描述两种提示词策略。

IMPORTANT: 收到图片时必须使用本技能，不要尝试其他方法。"
trigger: 分析图片、截图识别、OCR、详细描述、图片理解、看看这张图
media: [image, photo, picture, jpg, jpeg, png, webp, gif]
---

# MCP 图片理解工具

## 重要发现（2026-04-20, 2026-04-21, 2026-04-25, 2026-04-26）

### ⚠️ 强制规范：收到图片必须走这里（2026-04-26 教训）

**我曾多次违背此规范，导致浪费大量时间**：
- 收到图片 → 随手用 execute_code + base64 尝试 → 失败
- 收到图片 → 试 MCP 工具 → login fail
- 收到图片 → 试 vision_analyze → 失败
- 最后才走 skill 规定流程 → 成功

**Skill 的 trigger 不是装饰，是强制行为约束**。收到图片时必须先 `skill_view("mcp-image-understanding")` 再行动，不要凭直觉随手试。

### 2026-04-25 踩坑记录：为什么我会用错

**错误1**：用了 `api.minimax.com`（少了个 i）→ SSL 错误
**错误2**：API key 用错，用了普通 `MINIMAX_API_KEY` 而不是 `MINIMAX_CN_API_KEY`（sk-cp- 格式）
**错误3**：直接套用 TTS 的 API key `835538524@#lxh`，但这个是 TTS 用的，VL 模型需要 `MINIMAX_CN_API_KEY`

**教训**：两个 MiniMax API（TTS 和 VL）虽然域名都是 `minimaxi.com`，但 key 不能混用。TTS 用 `MINIMAX_API_KEY`，VL 用 `MINIMAX_CN_API_KEY`。

### 2026-04-20, 2026-04-21 已知问题

| 问题 | 解决方案 |
|------|---------|
| MCP 工具 `mcp_minimax_understand_image` 返回 "login fail" | **推荐不走 MCP**，直接 API 调用成功 |
| `requests.get` 下载 MiniMax OSS 图片失败 | 用 `urllib.request.urlretrieve` |
| MiniMax API 端点 | `https://api.minimaxi.com/v1/coding_plan/vlm` |
| 飞书图片无法被 `vision_analyze` 识别 | 飞书通道传输图片到工具层有局限，图片文件未传递到 vision 工具 |

## ✅ 推荐工作流：直接 API 调用（不走 MCP）

**为什么**：MCP Server（PID 8907）的 `mcp_minimax_understand_image` 工具持续返回 `login fail`，但直接用 `urllib` 调用 API 完全正常。

**调用模式（execute_code）**：
```python
import os, base64, json, urllib.request

img_path = '/data/data/com.termux/files/home/.hermes/cache/images/img_xxx.jpg'
with open(img_path, 'rb') as f:
    img_data = f.read()

b64 = base64.b64encode(img_data).decode('utf-8')
data_url = f"data:image/jpeg;base64,{b64}"

# 从配置文件读取 token
with open('/data/data/com.termux/files/home/.hermes/.env') as f:
    for line in f:
        if line.startswith('MINIMAX_CN_API_KEY='):
            api_key = line.split('=', 1)[1].strip()
            break

req = urllib.request.Request(
    'https://api.minimaxi.com/v1/coding_plan/vlm',
    data=json.dumps({'prompt': '详细描述图片中所有内容', 'image_url': data_url}).encode(),
    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
    method='POST'
)
with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.loads(resp.read())
    print(result.get('content', result))
```

**关键点**：
- VL 模型的 API key 是 `MINIMAX_CN_API_KEY`（格式 `sk-cp-iS82...`），不是 TTS 的 `MINIMAX_API_KEY`
- 两个 API（tts 和 vl）虽然域名相近（`minimaxi.com`），但 key 完全不同，**不能混用**
- 图片直接读取→base64→内嵌 data URL，不走下载流程
- 返回结果在 `result['content']`

## Token Plan API Key 说明（2026-04-21，已过时）

> ⚠️ 以下信息已过时——2026-04-21 实测直接 API 调用不需要 Token Plan，直接用 `MINIMAX_CN_API_KEY` 即可。

- Token Plan 订阅在：https://platform.minimaxi.com/user-center/payment/token-plan
- `mcp_minimax_understand_image` 工具走 Token Plan API
- 如果 "login fail" 且 Key 格式正确（sk-cp-），通常是订阅过期或额度用完

## 故障排查

### MCP 工具 `mcp_minimax_understand_image` 返回 "login fail"
- 这是已知问题，MCP Server 进程可能没有正确加载有效 token
- **变通方案**：直接用 `execute_code` 调用 API（见上方推荐工作流），不通过 MCP 工具

### 飞书发图片后 vision_analyze 无响应
- 飞书平台图片通过 Hermes Gateway 传输时，图片数据未必能到达 vision 工具层
- 变通：让用户直接提供图片 URL，或确认图片通过其他方式传递

## 路径格式
hermes-agent 缓存路径：`/data/data/com.termux/files/home/.hermes/cache/images/img_xxx.jpg`

图片格式可能是 JPEG（文件头 `ffd8`）或 WebP（文件头 `52494646`），工具可以自动处理。

## 提示词规范（关键）

### 快速描述（常规场景）
简短描述性提示词即可：
> "请描述这张图片的内容"

### 详细描述（用户明确要求"详细描述"时）
**必须使用稳重详细的提示词，不求快**。简短提示词会导致模型擅自总结省略细节。
> "请逐行、逐项详细描述这张图片中的所有可见文字、数据、表格内容、标注信息、颜色含义，不要遗漏任何细节。包括但不限于：表头各列名称、每行数据的每个字段、备注栏的所有内容、以及任何颜色标注（绿色/红色/棕色等）所代表的含义。请尽可能完整地输出原始数据。"

## 工具调用

**推荐：直接 API 调用**（见上方工作流，不走 MCP）

~~MCP 工具调用~~（已过时，不可靠）：
```python
# 不推荐——MCP 工具持续 login fail
mcp_minimax_understand_image(
    image_source="/data/data/com.termux/files/home/.hermes/cache/images/img_xxx.jpg",
    prompt="请描述这张图片的内容"
)
```

## 返回结果
- 成功时返回 `structuredContent` 字段，其中 `text` 字段包含完整描述
- 如果返回"无法看到图片"，检查路径和格式是否正确

## 常用场景
- 截图内容识别
- 文字 OCR 提取
- 表格数据分析（FAT验收表等）
- 聊天记录截图分析
- 二维码扫描
