---
name: feishu-send-image
description: Send images to Feishu users via lark-oapi SDK. Handles upload (CreateImage API) then send (msg_type=image). DM uses open_id; group uses chat_id. Works for current-session DM without needing explicit ID lookup.
version: 1.1.1
author: Hermes Agent
license: MIT
dependencies: [lark-oapi]
metadata:
  hermes:
    tags: [feishu, image, messaging]
    platform: feishu
---

# Feishu Send Image

Send a local image file to a Feishu user or channel via lark-oapi SDK.

## Quick Usage

```python
import sys, os, io
sys.path.insert(0, '/data/data/com.termux/files/home/hermes-agent')
import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateImageRequest, CreateImageRequestBody, CreateMessageRequest, CreateMessageRequestBody

def load_env_key(prefix):
    with open(os.path.expanduser('~/.hermes/.env')) as f:
        for line in f:
            line = line.strip()
            if '=' in line and prefix.upper() in line.upper():
                return line.split('=', 1)[1].strip()
    return None

app_id = load_env_key('FEISHU_APP_ID')
app_secret = load_env_key('FEISHU_APP_SECRET')
client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()

with open(image_path, 'rb') as f:
    img_file = io.BytesIO(f.read())
img_file.name = os.path.basename(image_path)

upload_resp = client.im.v1.image.create(
    CreateImageRequest.builder()
    .request_body(CreateImageRequestBody.builder()
        .image_type('message').image(img_file).build())
    .build())
image_key = upload_resp.data.image_key

user_open_id = 'ou_58af23392d77ef07bc19cb35bcec234d'
msg_resp = client.im.v1.message.create(
    CreateMessageRequest.builder()
    .receive_id_type('open_id')
    .request_body(CreateMessageRequestBody.builder()
        .receive_id(user_open_id).msg_type('image')
        .content(f'{{"image_key": "{image_key}"}}').build())
    .build())
print(f'Message ID: {msg_resp.data.message_id}')
```

## receive_id_type Cheatsheet

| Type | Format | Use When |
|------|--------|---------|
| `open_id` | `ou_...` | DM to user（需要预先查询用户的 open_id）|
| `chat_id` | `oc_...` | Group chat |
| **DM 也可用 chat_id** | `oc_...`（DM chat_id）| 直接用 channel_directory.json 里的 DM 的 `oc_` ID，配合 `receive_id_type='chat_id'` 发送，无需查 open_id |

**实测（2026-04-28）**：DM 的 chat_id（`oc_2e5cc02fdda5aef65a7f9ca03127eda5`）配合 `receive_id_type='chat_id'` 可正常发送图片，无需查用户的 open_id。

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `code=230001 invalid receive_id` | Wrong `receive_id_type` | Use `open_id` for `ou_` IDs, `chat_id` for `oc_` IDs |
| `code=99991663` | Image file too large | Compress before uploading |
| `code=99992361 open_id cross app` | Bot identity cannot send to user in DM | **Cannot fix via API** — image upload (image_type=message) + raw image_key must be delivered another way (file path / URL) |
| Upload succeeds but send fails | `receive_id` is `chat_id` but used with `open_id` type | Use `receive_id_type='chat_id'` for group sends |

## MiniMax Image Generation → Feishu Pipeline

```python
import urllib.request, os, io, json, sys
sys.path.insert(0, '/data/data/com.termux/files/home/hermes-agent')
import lark_oapi as lark
from lark_oapi.api.im.v1 import CreateImageRequest, CreateImageRequestBody, CreateMessageRequest, CreateMessageRequestBody

def load_env_key(prefix):
    with open(os.path.expanduser('~/.hermes/.env')) as f:
        for line in f:
            line = line.strip()
            if '=' in line and prefix.upper() in line.upper():
                return line.split('=', 1)[1].strip()
    return None

# Step 1: Generate via MiniMax
api_key = load_env_key('MINIMAX')
data = json.dumps({
    "model": "image-01",
    "prompt": "Your prompt here",
    "aspect_ratio": "16:9",
    "response_format": "url"
}).encode()
req = urllib.request.Request(
    'https://api.minimaxi.com/v1/image_generation',
    data=data,
    headers={
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    },
    method='POST'
)
with urllib.request.urlopen(req, timeout=120) as resp:
    image_url = json.loads(resp.read())['data']['image_urls'][0]

# Step 2: Download (urllib ONLY — requests fails on MiniMax OSS URLs)
save_path = os.path.expanduser('~/generated_image.jpg')
urllib.request.urlretrieve(image_url, save_path)

# Step 3: Upload to Feishu
app_id = load_env_key('FEISHU_APP_ID')
app_secret = load_env_key('FEISHU_APP_SECRET')
client = lark.Client.builder().app_id(app_id).app_secret(app_secret).build()

with open(save_path, 'rb') as f:
    img_file = io.BytesIO(f.read())
img_file.name = os.path.basename(save_path)

upload = client.im.v1.image.create(
    CreateImageRequest.builder()
    .request_body(CreateImageRequestBody.builder()
        .image_type('message').image(img_file).build())
    .build())
image_key = upload.data.image_key

# Step 4: Send to DM
user_open_id = 'ou_58af23392d77ef07bc19cb35bcec234d'
msg = client.im.v1.message.create(
    CreateMessageRequest.builder()
    .receive_id_type('open_id')
    .request_body(CreateMessageRequestBody.builder()
        .receive_id(user_open_id).msg_type('image')
        .content(f'{{"image_key": "{image_key}"}}').build())
    .build())
print(f'Done: {msg.data.message_id}')
```
