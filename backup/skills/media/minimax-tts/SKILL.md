---
name: minimax-tts
description: MiniMax Text-to-Speech via API v2 — generates audio using `speech-2.8-hd` model, converts to OGG/opus via ffmpeg, sends to Feishu with duration parameter. Requires MINIMAX_CN_API_KEY and Feishu credentials.
version: 2.1.0
author: Hermes Agent
license: MIT
dependencies: [requests, ffmpeg]
metadata:
  hermes:
    tags: [minimax, tts, audio, feishu]
    platform: feishu
---

# MiniMax TTS

MiniMax 文字转语音，通过 `speech-2.8-hd` 模型生成音频，转换为 OGG/opus 格式后发送到飞书。

## 完整流程（已验证可用）

```python
import requests, json, subprocess, os, urllib.parse

def minimax_tts_to_feishu(text, voice_id="female-tianmei", speed=1.0, chat_id=None):
    """MiniMax TTS -> ffmpeg转OGG/opus -> 发送飞书语音消息"""

    # 1. 读取凭证
    with open("/data/data/com.termux/files/home/.hermes/.env") as f:
        creds = dict(line.strip().split("=", 1) for line in f if "=" in line)
    api_key = creds["MINIMAX_CN_API_KEY"]
    app_id = creds["FEISHU_APP_ID"]
    app_secret = creds["FEISHU_APP_SECRET"]
    if not chat_id:
        chat_id = "oc_2e5cc02fdda5aef65a7f9ca03127eda5"  # 刘小豪

    # 2. MiniMax TTS（关键：用 x-www-form-urlencoded，不是 JSON）
    #    voice_id 和 speed 放顶层，不要嵌套在 voice_setting 里
    form_data = urllib.parse.urlencode({
        "model": "speech-2.8-hd",
        "text": text,
        "voice_id": voice_id,
        "speed": speed,
    })
    resp = requests.post(
        "https://api.minimaxi.com/v1/t2a_v2",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/x-www-form-urlencoded"  # ✅ 必须是这个
        },
        data=form_data, timeout=30
    )
    data = resp.json()
    mp3_bytes = bytes.fromhex(data["data"]["audio"])  # ✅ hex 解码

    # 3. ffmpeg 转换为 OGG/opus（飞书手机端必须用此格式）
    home = "/data/data/com.termux/files/home"
    mp3_path = f"{home}/voice_src.mp3"
    ogg_path = f"{home}/voice_final.ogg"
    with open(mp3_path, "wb") as f:
        f.write(mp3_bytes)

    subprocess.run([
        "ffmpeg", "-y", "-i", mp3_path,
        "-c:a", "libopus", "-b:a", "128k", "-vbr", "on", "-frame_duration", "20",
        ogg_path
    ], capture_output=True)

    # 获取时长（毫秒）
    dur = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", ogg_path],
        capture_output=True, text=True
    )
    duration_ms = int(float(dur.stdout.strip()) * 1000)

    with open(ogg_path, "rb") as f:
        ogg_bytes = f.read()

    # 4. 获取飞书 token
    r2 = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret}, timeout=60
    )
    token = r2.json()["tenant_access_token"]

    # 5. 上传（file_type=opus，文件格式 ogg）
    r3 = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/files",
        files={
            "file": ("voice.ogg", ogg_bytes, "audio/ogg"),
            "file_name": (None, "voice.ogg"),
            "file_type": (None, "opus"),
        },
        headers={"Authorization": f"Bearer {token}"}, timeout=30
    )
    file_key = r3.json()["data"]["file_key"]

    # 6. 发送（关键：用 receive_id_type=chat_id，不是 open_id）
    #    chat_id 以 "oc_" 开头 → 用 chat_id
    #    open_id 以 "ou_" 开头 → 用 open_id
    r4 = requests.post(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "receive_id": chat_id,  # ✅ 用 chat_id，不是 open_id
            "msg_type": "audio",
            "content": json.dumps({"file_key": file_key, "duration": duration_ms})
        }, timeout=30
    )
    return r4.json()
```

## 关键要点（踩坑记录）

### 0. 请求格式：必须用 x-www-form-urlencoded
API 要求的 `Content-Type` 是 **`application/x-www-form-urlencoded`**，不是 `application/json`。
用 JSON 会静默失败，HTTP 200 但返回 `{"base_resp": {"status_code": 2013, "status_msg": "invalid params, "empty field"}}`。

```python
# ✅ 正确
form_data = urllib.parse.urlencode({"model": "speech-2.8-hd", "text": text, "voice_id": voice_id, "speed": speed})
requests.post(url, headers={"Content-Type": "application/x-www-form-urlencoded"}, data=form_data)

# ❌ 错误（静默失败，返回 2013）
requests.post(url, headers={"Content-Type": "application/json"}, json={...})
```

### 1. 音频解码：hex 不是 base64
API 返回的 `audio` 字段是 **hex 字符串**，必须用 `bytes.fromhex()` 解码。
```python
audio_bytes = bytes.fromhex(resp_data["data"]["audio"])  # ✅ 正确
# audio_bytes = base64.b64decode(...)  # ❌ 会变成噪音
```

### 2. 飞书格式：必须用 OGG/opus
电脑飞书可以播 MP3，但**手机飞书必须用 OGG/opus 格式**，否则手机端播放异常（杂音/无法播放）。
- 用 `ffmpeg -i input.mp3 -c:a libopus -b:a 128k output.ogg` 转换
- 上传时 `file_type` 仍填 `opus`，文件扩展名用 `.ogg`

### 3. duration 参数必须传毫秒
发送 audio 消息时，`content` 里的 duration 单位是**毫秒**：
```python
duration_ms = int(float(ffprobe_duration) * 1000)
```

### 4. voice_setting 只用 voice_id + speed
- **pitch / volume 参数不要传**，传了会变噪音
- **speed 用 float**，如 `1.0`（不是 100，也不是 110）

### 5. 飞书上传：requests.files 方式可行
之前测试手动拼接 multipart 报 234001 错误，用 `requests.files` 方式上传成功。

## 可用音色

| 音色 ID | 名称 | 状态 |
|---------|------|------|
| `female-tianmei` | 甜美女声 | ✅ 默认最满意 |
| `female-yujie` | 御姐 | ✅ 备选 |
| `male-qn-qingse` | 清澈少年 | ✅ 男声清晰 |
| `Chinese (Mandarin)_News_Anchor` | 新闻女声 | 待测 |
| `Chinese (Mandarin)_Sweet_Lady` | 甜美女声2 | 待测 |
| `lovely_girl` | 萌萌女童 | 待测 |
| `qiaopi_mengmei` | 俏皮萌妹 | 待测 |
| `female-shaonv` | 少女 | 待测 |
| `Cantonese_GentleLady` | 粤语温柔女声 | 待测 |

## 已知问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 手机飞书无法播放/杂音 | 用了 MP3 格式 | 用 ffmpeg 转 OGG/opus |
| audio 消息时长显示 0 | 没传 duration 参数 | 传 duration 毫秒值 |
| 音频全是噪音 | 用了 base64 解码 | 改用 `bytes.fromhex()` |
| API 返回 2013 | pitch 传了小数，或用了 output_format | 去掉这些参数 |
| API 返回 2013 invalid params | 请求体用 JSON 而非 form-urlencoded，或字段为空 | 用 `urllib.parse.urlencode` + `data=` 而非 `json=` |
| API 返回 2061 | 模型名错误（如 speech-02-hd） | 改用 `speech-2.8-hd` |
| Feishu 发送报 99992361 open_id cross app | 用 `receive_id_type=open_id` 发了 chat_id | chat_id（oc_ 开头）用 `receive_id_type=chat_id` |
| duration 显示 0 但可播放 | 只传了 file_key 没传 duration | 加上 duration 参数 |
| ffmpeg 找不到 | Termux 默认没有 | `apt-get install -y ffmpeg` |
