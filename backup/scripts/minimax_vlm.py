#!/usr/bin/env python3
"""
MiniMax VLM (Vision) API 独立调用脚本
不依赖 MCP 工具，直接用 urllib 调用 MiniMax 图片理解 API

用法:
  python3 minimax_vlm.py <图片路径> "<prompt>"
  python3 minimax_vlm.py /path/to/image.jpg "描述图片内容"

Key 存储位置: ~/.hermes/secrets/minimax_vlm_key.txt
"""

import base64
import io
import json
import os
import ssl
import sys
import urllib.request
from pathlib import Path

# Add local libs path for Pillow
_SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPT_DIR / "pylibs"))

API_URL = "https://api.minimaxi.com/v1/coding_plan/vlm"
KEY_PATH = Path.home() / ".hermes" / "secrets" / "minimax_vlm_key.txt"


def get_api_key() -> str:
    """从 secrets 目录读取 API key"""
    if not KEY_PATH.exists():
        raise FileNotFoundError(
            f"Key file not found: {KEY_PATH}\n"
            "Please create it with your MiniMax API key."
        )
    return KEY_PATH.read_text().strip()


def encode_image(image_path: str) -> str:
    """将本地图片转为 base64 data URL"""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    suffix = path.suffix.lower()
    mime_map = {'.jpg': 'jpeg', '.jpeg': 'jpeg', '.png': 'png', '.webp': 'webp'}
    mime = mime_map.get(suffix, 'jpeg')

    img_bytes = path.read_bytes()

    # 压缩大于 500KB 的图片
    from PIL import Image
    if len(img_bytes) > 500 * 1024:
        img = Image.open(path)
        w, h = img.size
        if w > 1024:
            ratio = 1024 / w
            img = img.resize((1024, int(h * ratio)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format=mime.upper(), quality=80)
        img_bytes = buf.getvalue()

    b64 = base64.b64encode(img_bytes).decode()
    return f"data:image/{mime};base64,{b64}"


def call_vlm(image_path: str, prompt: str) -> str:
    """调用 MiniMax VLM API，返回文本描述"""
    api_key = get_api_key()
    image_url = encode_image(image_path)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    payload = json.dumps({
        "prompt": prompt,
        "image_url": image_url
    }).encode()

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    with urllib.request.urlopen(req, context=ctx, timeout=60) as resp:
        result = json.loads(resp.read())

    content = result.get("content", "")
    if not content:
        raise ValueError(f"No content in VLM response: {result}")
    return content


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    image_path = sys.argv[1]
    prompt = sys.argv[2]

    try:
        result = call_vlm(image_path, prompt)
        print(result)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
