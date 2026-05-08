#!/usr/bin/env python3
"""
星际流光 V2 — 增强版
更高密度 + 更清晰分辨率 + 更丰富色彩层次
"""

import numpy as np
import subprocess
import sys
import os
from math import sin, cos, sqrt, pi, atan2, exp
from random import randint

# ─── CONFIG ──────────────────────────────────────────────────────────────────
RES_W, RES_H = 200, 80        # 更高分辨率
FPS = 24
DURATION = 10                   # 10秒
CELL_W, CELL_H = 10, 18        # 更大字符像素
VIRTUAL_W = RES_W * CELL_W     # 2000px
VIRTUAL_H = RES_H * CELL_H     # 1440px
TOTAL_FRAMES = FPS * DURATION

OUT_MP4 = os.path.expanduser("~/.hermes/cron/output/stellar_flow_v2.mp4")
OUT_GIF = os.path.expanduser("~/.hermes/cron/output/stellar_flow_v2.gif")
os.makedirs(os.path.dirname(OUT_MP4), exist_ok=True)

FONT_PATH = "/system/fonts/DroidSansMono.ttf"

# ─── COLOR PALETTE ───────────────────────────────────────────────────────────
def hsv_to_rgb(h, s, v):
    h = h % 1.0
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    RGB = [(v, t, p), (q, v, p), (p, v, t), (p, t, v), (t, p, v), (v, p, q)]
    return tuple(int(x * 255) for x in RGB[i])

# 极光色系：冰蓝 → 青绿 → 翠绿 → 紫罗兰 → 玫瑰金
AURORA_COLORS = [
    (0.58, 0.85, 1.00),   # 冰蓝
    (0.45, 0.90, 0.85),   # 青绿
    (0.38, 0.95, 0.65),   # 翠绿
    (0.72, 0.80, 1.00),   # 淡紫
    (0.82, 0.70, 0.95),   # 紫罗兰
    (0.95, 0.60, 0.85),   # 玫瑰
    (1.00, 0.85, 0.50),   # 暖金
    (0.55, 0.95, 1.00),   # 天蓝
]

rng = np.random.default_rng(42)

# ─── NUMPY HELPERS ───────────────────────────────────────────────────────────
def clamp(val, lo=0.0, hi=1.0):
    return max(lo, min(hi, val))

# ─── PARTICLES ───────────────────────────────────────────────────────────────
N_STARS = 400
N_SPARKLES = 120
N_METEORS = 30

stars = {
    'x': rng.uniform(0, RES_W, N_STARS),
    'y': rng.uniform(0, RES_H, N_STARS),
    'vx': rng.uniform(-0.05, 0.05, N_STARS),
    'vy': rng.uniform(-0.08, 0.02, N_STARS),
    'life': rng.uniform(0.3, 1.0, N_STARS),
    'size': rng.uniform(0.5, 2.0, N_STARS),
    'hue': rng.uniform(0, 1, N_STARS),
    'twinkle_offset': rng.uniform(0, 2*pi, N_STARS),
    'twinkle_speed': rng.uniform(1.0, 3.0, N_STARS),
}

sparkles = {
    'x': rng.uniform(0, RES_W, N_SPARKLES),
    'y': rng.uniform(0, RES_H, N_SPARKLES),
    'vx': rng.uniform(-0.1, 0.1, N_SPARKLES),
    'vy': rng.uniform(-0.2, -0.05, N_SPARKLES),
    'life': rng.uniform(0, 1, N_SPARKLES),
    'decay': rng.uniform(0.005, 0.02, N_SPARKLES),
    'hue': rng.uniform(0, 1, N_SPARKLES),
    'size': rng.uniform(0.3, 1.5, N_SPARKLES),
}

meteors = []
for _ in range(N_METEORS):
    meteors.append({
        'x': rng.uniform(-0.2, 1.2),
        'y': rng.uniform(-0.1, 0.5),
        'vx': rng.uniform(0.3, 0.8),
        'vy': rng.uniform(0.4, 0.9),
        'life': rng.uniform(0, 1),
        'length': rng.uniform(3, 8),
        'hue': rng.uniform(0.55, 0.70),
    })

# ─── FIELD FUNCTIONS ──────────────────────────────────────────────────────────

def wave_field(x, y, t, freq=3.0, phase=0.0):
    r = sqrt(x*x + y*y)
    v = 0.5 + 0.5 * sin(r * freq * 0.2 - t * 2.5 + phase)
    return v

def aurora_field(x, y, t):
    """横向极光带，多层正弦叠加"""
    band1 = sin(y * 0.6 + t * 1.8) * 0.5 + 0.5
    band2 = sin(y * 0.35 - t * 1.2 + 1.5) * 0.3 + 0.7
    band3 = sin(y * 0.8 + t * 2.5 + 3.0) * 0.2 + 0.8
    wave = sin(x * 0.15 + t * 0.8) * 0.15 + 0.85
    return band1 * 0.4 + band2 * 0.35 + band3 * 0.25 * wave

def voronoi_energy(x, y, t, pts, speed=1.0):
    """Voronoi-style energy field from moving points"""
    min_d = 999.0
    for px, py, bx, by in pts:
        dx = x - (px + bx * sin(t * speed * 0.7))
        dy = y - (py + by * cos(t * speed * 0.5))
        d = sqrt(dx*dx + dy*dy)
        if d < min_d:
            min_d = d
    return exp(-min_d * 3.0)

def spiral_field(x, y, t, cx, cy, arms=3):
    """Spiral galaxy arms"""
    dx = x - cx
    dy = y - cy
    r = sqrt(dx*dx + dy*dy)
    if r < 0.001:
        return 0.0
    angle = atan2(dy, dx)
    spiral = sin(angle * arms + r * 12.0 - t * 1.5) * 0.5 + 0.5
    falloff = exp(-r * 3.0)
    return spiral * falloff

# Pre-compute galaxy core points
GALAXY_PTS = [(cos(a)*0.15, sin(a)*0.15, cos(a)*0.08, sin(a)*0.08)
              for a in np.linspace(0, 2*pi, 8)]

# ─── PARTICLE UPDATERS ───────────────────────────────────────────────────────

def update_stars(dt):
    for i in range(N_STARS):
        stars['x'][i] += stars['vx'][i]
        stars['y'][i] += stars['vy'][i]
        if stars['y'][i] < -0.05 or stars['x'][i] < -0.05 or stars['x'][i] > 1.05:
            stars['x'][i] = rng.uniform(0, 1)
            stars['y'][i] = rng.uniform(0.9, 1.1)
            stars['vx'][i] = rng.uniform(-0.03, 0.03)
            stars['vy'][i] = rng.uniform(-0.06, -0.01)
            stars['life'][i] = rng.uniform(0.4, 1.0)

def update_sparkles(dt):
    for i in range(N_SPARKLES):
        sparkles['x'][i] += sparkles['vx'][i]
        sparkles['y'][i] += sparkles['vy'][i]
        sparkles['life'][i] -= sparkles['decay'][i]
        if sparkles['life'][i] <= 0:
            sparkles['x'][i] = rng.uniform(0, 1)
            sparkles['y'][i] = rng.uniform(0.5, 1.1)
            sparkles['vx'][i] = rng.uniform(-0.08, 0.08)
            sparkles['vy'][i] = rng.uniform(-0.15, -0.03)
            sparkles['life'][i] = 1.0
            sparkles['decay'][i] = rng.uniform(0.008, 0.025)
            sparkles['hue'][i] = rng.uniform(0, 1)

def update_meteors(dt):
    for m in meteors:
        m['x'] += m['vx'] * dt * 0.15
        m['y'] += m['vy'] * dt * 0.15
        m['life'] -= dt * 0.4
        if m['life'] <= 0 or m['y'] > 1.3 or m['x'] > 1.3:
            m['x'] = rng.uniform(-0.2, 0.3)
            m['y'] = rng.uniform(-0.1, 0.2)
            m['vx'] = rng.uniform(0.2, 0.6)
            m['vy'] = rng.uniform(0.3, 0.7)
            m['life'] = 1.0
            m['length'] = rng.uniform(3, 8)
            m['hue'] = rng.uniform(0.55, 0.70)

# ─── SCENE BUILDERS ───────────────────────────────────────────────────────────

def build_galaxy_background(t):
    """银河系中心 — 螺旋臂 + 核心光芒"""
    canvas = np.zeros((RES_H, RES_W, 3), dtype=np.float32)
    cx, cy = RES_W * 0.5, RES_H * 0.5

    # 背景星场 (微弱)
    for i in range(N_STARS):
        sx = int(stars['x'][i] * RES_W)
        sy = int(stars['y'][i] * RES_H)
        if 0 <= sx < RES_W and 0 <= sy < RES_H:
            tw = sin(t * stars['twinkle_speed'][i] + stars['twinkle_offset'][i]) * 0.3 + 0.7
            brightness = stars['life'][i] * tw * 0.3
            if brightness > 0.05:
                col = hsv_to_rgb(stars['hue'][i], 0.3, brightness)
                canvas[sy, sx] = col

    # 螺旋臂
    for y in range(RES_H):
        for x in range(RES_W):
            nx, ny = x / RES_W, y / RES_H
            d = spiral_field(nx - 0.5, ny - 0.5, t, 0, 0, arms=4)
            if d > 0.1:
                hue = (nx * 0.3 + ny * 0.2 + t * 0.03) % 1.0
                col = hsv_to_rgb(hue, 0.8, d * 0.7)
                canvas[y, x] += col

    # 核心发光
    for dy in range(-20, 21):
        for dx in range(-35, 36):
            nx, ny = cx + dx, cy + dy
            if 0 <= int(nx) < RES_W and 0 <= int(ny) < RES_H:
                dist = sqrt(dx*dx * 0.5 + dy*dy) / 35.0
                if dist < 1.0:
                    glow = (1.0 - dist) ** 2.0
                    col = hsv_to_rgb(0.62, 0.5, glow * 1.2)
                    canvas[int(ny), int(nx)] += col

    return canvas

def build_aurora_layer(t, canvas):
    """极光帘幕叠加"""
    for y in range(RES_H):
        for x in range(RES_W):
            # 多重波动叠加
            w = wave_field(x, y, t, freq=2.5)
            aur = aurora_field(x, y, t)
            v = voronoi_energy(x / RES_W, y / RES_H, t, GALAXY_PTS, speed=0.8)
            intensity = w * 0.3 + aur * 0.5 + v * 0.4

            if intensity > 0.12:
                hue = (x / RES_W * 0.35 + t * 0.06 + y / RES_H * 0.1) % 1.0
                sat = 0.75 + intensity * 0.25
                val = min(1.0, intensity * 2.2)
                col = hsv_to_rgb(hue, sat, val)
                alpha = min(0.65, intensity * 1.5)
                canvas[y, x] = canvas[y, x] * (1 - alpha) + np.array(col) * alpha

def build_nebula_pulse(t, canvas, phase_start=0, phase_end=10):
    """星云脉冲 — 中间段专用效果"""
    phase_t = clamp((t - phase_start) / max(0.1, phase_end - phase_start))
    pulse = sin(phase_t * pi)  # 0→1→0 envelope

    cx1, cy1 = 0.25 + 0.05 * sin(t * 0.4), 0.35 + 0.05 * cos(t * 0.3)
    cx2, cy2 = 0.75 + 0.05 * cos(t * 0.35 + 1.5), 0.65 + 0.05 * sin(t * 0.45 + 2.0)

    for y in range(RES_H):
        for x in range(RES_W):
            nx, ny = x / RES_W, y / RES_H
            d1 = sqrt((nx - cx1)**2 + (ny - cy1)**2)
            d2 = sqrt((nx - cx2)**2 + (ny - cy2)**2)
            nebula = (exp(-d1 * 5.0) * 0.6 + exp(-d2 * 4.0) * 0.4) * pulse

            if nebula > 0.05:
                hue = ((nx + ny) * 0.2 + t * 0.04) % 1.0
                col = hsv_to_rgb(hue, 0.85, min(1.0, nebula * 2.5))
                alpha = min(0.55, nebula * 2.0)
                canvas[y, x] = canvas[y, x] * (1 - alpha) + np.array(col) * alpha

def draw_sparkles(t, canvas, intensity=1.0):
    """闪烁星点"""
    for i in range(N_SPARKLES):
        sx = int(sparkles['x'][i] * RES_W)
        sy = int(sparkles['y'][i] * RES_H)
        if 0 <= sx < RES_W and 0 <= sy < RES_H:
            life = sparkles['life'][i]
            hue = sparkles['hue'][i]
            val = life * sparkles['size'][i] * intensity
            col = hsv_to_rgb(hue, 0.4, min(1.0, val))
            canvas[sy, sx] = np.array(col) * life + canvas[sy, sx] * (1 - life)

def draw_meteors(canvas, intensity=1.0):
    """流星轨迹"""
    for m in meteors:
        if m['life'] <= 0:
            continue
        life = m['life']
        for seg in range(int(m['length'])):
            tx = int((m['x'] - m['vx'] * seg * 0.03) * RES_W)
            ty = int((m['y'] - m['vy'] * seg * 0.03) * RES_H)
            if 0 <= tx < RES_W and 0 <= ty < RES_H:
                fade = (1.0 - seg / m['length']) * life * intensity
                col = hsv_to_rgb(m['hue'], 0.6, fade)
                canvas[ty, tx] = np.array(col) * fade + canvas[ty, tx] * (1 - fade * 0.5)

def draw_core_glow(canvas, t, cx, cy, intensity):
    """中心光晕"""
    for dy in range(-12, 13):
        for dx in range(-20, 21):
            nx, ny = cx + dx, cy + dy
            if 0 <= int(nx) < RES_W and 0 <= int(ny) < RES_H:
                dist = sqrt(dx*dx * 0.6 + dy*dy) / 20.0
                if dist < 1.0:
                    glow = (1.0 - dist) ** 1.5 * intensity
                    col = hsv_to_rgb(0.60 + sin(t) * 0.05, 0.4, glow * 1.5)
                    canvas[int(ny), int(nx)] += np.array(col) * glow

# ─── MAIN RENDER ─────────────────────────────────────────────────────────────

def render_frame(t, dt):
    # Section timing
    # 0-2s: Galaxy emergence
    # 2-4s: Aurora + stars
    # 4-7s: Full nebula + aurora + meteors + sparkles
    # 7-10s: Dissolve + meteors

    canvas = build_galaxy_background(t)

    if t < 3.0:
        # Opening: galaxy emerges with aurora rising
        build_aurora_layer(t, canvas)
        draw_core_glow(canvas, t, RES_W // 2, RES_H // 2, min(1.0, t / 2.5))
        update_stars(dt)
        update_sparkles(dt)
        draw_sparkles(t, canvas, intensity=0.6)

    elif t < 7.5:
        # Main section: full effects
        build_aurora_layer(t, canvas)
        build_nebula_pulse(t, canvas, phase_start=3.5, phase_end=7.0)
        update_stars(dt)
        update_sparkles(dt)
        update_meteors(dt)
        draw_sparkles(t, canvas, intensity=1.0)
        draw_meteors(canvas, intensity=1.0)

        # Pulsing core
        pulse = sin(t * 2.0) * 0.3 + 0.7
        draw_core_glow(canvas, t, RES_W // 2, RES_H // 2, pulse * 0.5)

    else:
        # Outro: fade to starfield
        fade = 1.0 - (t - 7.5) / 2.5
        build_aurora_layer(t, canvas)
        update_stars(dt)
        update_meteors(dt)
        draw_meteors(canvas, intensity=fade)
        draw_sparkles(t, canvas, intensity=fade * 0.7)
        draw_core_glow(canvas, t, RES_W // 2, RES_H // 2, fade * 0.3)

    # Tonemap
    return tonemap(canvas.astype(np.uint8))

def tonemap(canvas, gamma=0.70):
    """Adaptive tonemap — keep it vibrant, not washed out"""
    f = canvas.astype(np.float32)
    lo, hi = np.percentile(f[::4, ::4], [1, 99.0])
    if hi - lo < 15:
        hi = lo + 15
    f = np.clip((f - lo) / (hi - lo), 0, 1) ** gamma
    return (f * 255).astype(np.uint8)

# ─── ASCII -> IMAGE RENDERING ─────────────────────────────────────────────────

def render_frame_to_image(canvas, frame_num):
    """Render RGB canvas to high-res PNG via Pillow"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    W = RES_W * CELL_W
    H = RES_H * CELL_H
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_size = int(CELL_H * 0.85)
    try:
        font = ImageFont.truetype(FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()

    # Pre-compute char sizes
    char_w = CELL_W
    char_h = CELL_H

    for y in range(RES_H):
        for x in range(RES_W):
            r, g, b = canvas[y, x]
            brightness = (r * 0.299 + g * 0.587 + b * 0.114) / 255.0

            # High-density character ramp
            if brightness > 0.88:
                ch = "█"
            elif brightness > 0.72:
                ch = "▓"
            elif brightness > 0.56:
                ch = "▒"
            elif brightness > 0.40:
                ch = "░"
            elif brightness > 0.22:
                ch = "∙"
            elif brightness > 0.08:
                ch = "⋅"
            else:
                ch = " "

            # Compute text position — center each char in its cell
            try:
                bbox = font.getbbox(ch)
                cw = bbox[2] - bbox[0]
                ch_h = bbox[3] - bbox[1]
            except Exception:
                cw = char_w
                ch_h = char_h

            tx = x * char_w + (char_w - cw) // 2
            ty = y * char_h + (char_h - ch_h) // 2

            draw.text((tx, ty), ch, fill=(r, g, b), font=font)

    return img

# ─── ENCODE ──────────────────────────────────────────────────────────────────

def encode():
    print(f"Rendering {TOTAL_FRAMES} frames at {RES_W}×{RES_H} chars "
          f"({RES_W*CELL_W}×{RES_H*CELL_H}px)...")

    frame_dir = os.path.expanduser("~/.hermes/cron/output/frames_v2")
    os.makedirs(frame_dir, exist_ok=True)

    frames = []
    for frame_num in range(TOTAL_FRAMES):
        t = frame_num / FPS
        dt = 1.0 / FPS
        canvas = render_frame(t, dt)
        img = render_frame_to_image(canvas, frame_num)
        if img:
            frame_path = os.path.join(frame_dir, f"f_{frame_num:04d}.png")
            img.save(frame_path, "PNG", optimize=False)
            frames.append(frame_path)

        if frame_num % 24 == 0:
            print(f"  {frame_num}/{TOTAL_FRAMES} ({(frame_num*100)//TOTAL_FRAMES}%)")

    print(f"Encoding MP4 ({VIRTUAL_W}×{VIRTUAL_H})...")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frame_dir, "f_%04d.png"),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={VIRTUAL_W}:{VIRTUAL_H}",
        OUT_MP4
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"MP4 error: {r.stderr[-400:]}")
    else:
        print(f"✓ MP4: {OUT_MP4}")

    print("Encoding GIF...")
    gif_w = min(VIRTUAL_W, 800)
    gif_h = int(gif_w * VIRTUAL_H / VIRTUAL_W)
    cmd_gif = [
        "ffmpeg", "-y",
        "-framerate", "15",
        "-i", os.path.join(frame_dir, "f_%04d.png"),
        "-vf", f"fps=15,scale={gif_w}:{gif_h}:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        OUT_GIF
    ]
    r = subprocess.run(cmd_gif, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"GIF error: {r.stderr[-400:]}")
    else:
        print(f"✓ GIF: {OUT_GIF}")

    import shutil
    shutil.rmtree(frame_dir, ignore_errors=True)
    print("Done!")

if __name__ == "__main__":
    print("=" * 55)
    print("  ✦ 星际流光 V2 — 增强版 ✦")
    print("  Higher Density · Crisper Resolution · Richer Colors")
    print("=" * 55)
    print(f"  Grid: {RES_W}×{RES_H} chars")
    print(f"  Output: {RES_W*CELL_W}×{RES_H*CELL_H}px @ {FPS}fps")
    print(f"  Duration: {DURATION}s = {TOTAL_FRAMES} frames")
    print()
    encode()
    print(f"\n  → MP4: {OUT_MP4}")
    print(f"  → GIF: {OUT_GIF}")
