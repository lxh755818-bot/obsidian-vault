---
name: minimax-image-generation
description: Generate images via MiniMax Image-01 API using direct Python urllib calls. Supports text-to-image with aspect ratio control, quality templates, and character consistency via subject_reference. MCP tool is not available — always use direct API calls.
version: 1.1.0
author: Hermes Agent
license: MIT
dependencies: []
metadata:
  hermes:
    tags: [Image Generation, MiniMax, Text-to-Image, API]
    tools: []
---

# MiniMax Image Generation

> **⚠️ MCP tool `minimax_image_generate` is NOT available.**
> Always use the Direct API Call method below.

---

## API Configuration

**可用模型（2026-05-02 验证）：**
```
MiniMax-M2.7
MiniMax-M2.7-highspeed
MiniMax-M2.5
MiniMax-M2.5-highspeed
MiniMax-M2.1
MiniMax-M2.1-highspeed
MiniMax-M2
```
⚠️ `image-01` 模型不存在。不要使用。

| Item | Value |
|------|-------|
| Endpoint | `https://api.minimaxi.com/v1/image_generation` |
| Auth | Bearer token — **直接用字符串，不从文件读取**（文件会被截断） |
| Response | `response_format=url` → `result['data']['image_urls'][0]` (list)<br>`response_format=base64` → `result['data']['image_base64'][0]` (list of string, **take [0]**) |

**Key 来源**：从对话历史中取用户最近一次发送的完整 key 字符串。不要存文件。

**直接调用示例**：
```python
import urllib.request, json

key = "sk-cp-iS82DS1lLIfQoyy9H22Dbm4iYMU-..."  # 从对话取，不要从文件
body = json.dumps({"model": "image-01", ...}).encode()
# ⚠️ image-01 模型不存在，可用 MiniMax-M2.7 或 MiniMax-M2.5
```

---

## Aspect Ratio Guide

| Ratio | Best For |
|-------|----------|
| `1:1` | Square posts, profile, product thumbnails |
| `16:9` | Landscapes, wallpapers, banners, cinematic widescreen |
| `9:16` | Instagram stories, mobile wallpapers, vertical art, portraits |
| `3:2` | Photography, print layouts, posters |
| `2:3` | Portrait photography, magazine covers |

---

## Prompt Engineering

### Structure (in order of importance)

1. **Subject** — main focus
2. **Pose/Action** — what it is doing
3. **Style** — art style, genre, medium
4. **Lighting** — time of day, lighting mood
5. **Environment** — background, setting
6. **Quality tags** — `masterpiece, best quality, 8k`

### Positive Keywords

| Category | Keywords |
|----------|---------|
| Quality | `masterpiece, best quality, 8k, high resolution, highly detailed` |
| Lighting | `golden hour, soft lighting, dramatic lighting, backlit, neon glow` |
| Style | `photorealistic, cinematic, watercolor, oil painting, anime, digital art` |
| Detail | `intricate, sharp focus, macro shot, extreme detail` |
| Mood | `serene, dramatic, mysterious, vibrant, moody` |

### Negative Keywords

```
blurry, low quality, bad anatomy, distorted, ugly, deformed,
watermark, text, logo, cartoon, anime style
```

---

## Image Type Templates

### 1. Portrait / Character
```
Close-up portrait of a young woman with silver hair and bright blue eyes,
soft cinematic lighting, detailed skin texture, bokeh background,
photorealistic, 85mm lens, f/1.8 aperture, 8k, masterpiece
```
**Aspect:** `9:16` (portrait) or `1:1` (headshot)

### 2. Landscape / Nature
```
Majestic mountain landscape at golden hour, snow-capped peaks reflecting
golden light, pine forest in foreground, dramatic clouds, aerial drone shot,
photorealistic, cinematic color grading, 8k, masterpiece
```
**Aspect:** `16:9` (cinematic) or `3:2` (photography)

### 3. Fantasy / Concept Art
```
Epic fantasy landscape with floating islands, waterfalls cascading into clouds,
bioluminescent plants, ancient stone ruins with glowing runes, golden sunrise,
concept art style, highly detailed, digital painting, artstation, 8k, masterpiece
```
**Aspect:** `16:9` (widescreen) or `1:1` (square art)

### 4. Sci-Fi / Futuristic
```
Futuristic cyberpunk cityscape at night, neon signs in Japanese,
flying cars in distance, rain-slicked streets, blade runner aesthetic,
cinematic lighting, volumetric fog, 8k, masterpiece
```
**Aspect:** `16:9` (cinematic)

### 5. Product Shot
```
Minimalist product photography of an elegant perfume bottle on white marble,
soft studio lighting, subtle shadow, high-end luxury feel, 8k,
commercial photography, clean background
```
**Aspect:** `1:1` (e-commerce) or `16:9` (banner)

### 6. Architecture / City
```
Modern glass skyscraper at sunset, reflections on windows, aerial view,
golden hour lighting, urban cityscape, photorealistic, cinematic, 8k
```
**Aspect:** `16:9` or `9:16` (vertical city)

### 7. Vintage / Retro
```
1950s American diner interior, chrome counter, red leather booths,
vintage jukebox, warm incandescent lighting, film grain, nostalgic mood,
photorealistic, 8k
```
**Aspect:** `16:9` or `1:1`

---

## Subject Reference (Character Consistency)

1. Generate or upload a reference image
2. Base64-encode it
3. Pass as `subject_reference` in the API call

MiniMax will maintain character features across new poses/scenes.

---

## Direct API Call (Recommended: base64)

```python
import urllib.request, os, json, base64

url = "https://api.minimaxi.com/v1/image_generation"

api_key = None
env_path = os.path.expanduser('~/.hermes/.env')
with open(env_path, 'r') as f:
    for line in f:
        line = line.strip()
        if '=' in line and 'API' in line.upper() and 'MINIMAX' in line.upper():
            api_key = line.split('=', 1)[1].strip()
            break

data = json.dumps({
    "model": "image-01",
    "prompt": "Your detailed prompt here",
    "aspect_ratio": "16:9",
    "response_format": "base64"  # Preferred — avoids URL download 403 issues
}).encode('utf-8')

req = urllib.request.Request(url, data=data, headers={
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}, method='POST')

with urllib.request.urlopen(req, timeout=60) as resp:
    result = json.loads(resp.read().decode('utf-8'))
    # ⚠️ base64 returns a list, take [0]
    b64_str = result['data']['image_base64'][0]
    img_bytes = base64.b64decode(b64_str)

save_path = os.path.expanduser('~/generated_image.jpg')
with open(save_path, 'wb') as f:
    f.write(img_bytes)
print(f"Saved: {os.path.getsize(save_path)} bytes")
```

## Direct API Call (URL format — may fail in sandbox)

```python
# URL format: download via urllib
with urllib.request.urlopen(req, timeout=60) as resp:
    result = json.loads(resp.read().decode('utf-8'))
    image_url = result['data']['image_urls'][0]

save_path = os.path.expanduser('~/generated_image.jpg')
urllib.request.urlretrieve(image_url, save_path)  # May get 403 in sandbox
```

**Critical:**
- **`response_format: "base64"` returns a LIST** — `result['data']['image_base64']` is an array (e.g. `["/9j/4AAQ..."]`), always take `[0]`
- **`response_format: "url"` — URL download may fail with 403 in sandbox/execute_code environments**; prefer `base64` for reliability
- **Always use `urllib.request.urlretrieve`** — `requests.get` fails on MiniMax OSS URLs with encoded chars
- Endpoint: `api.minimaxi.com` (Chinese region), NOT `api.minimax.io`
