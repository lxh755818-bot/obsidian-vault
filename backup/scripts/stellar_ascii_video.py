#!/usr/bin/env python3
"""
星际流光 — Stellar Flow ASCII Art Video
Cosmic nebula meets aurora borealis in colored ASCII
"""

import numpy as np
import subprocess
import sys
import os
from math import sin, cos, sqrt, pi, atan2
from random import randint

# ─── CONFIG ──────────────────────────────────────────────────────────────────
RES_W, RES_H = 160, 50          # ASCII grid resolution
FPS = 24
DURATION = 8                    # seconds
CELL_W, CELL_H = 8, 16          # font cell size in pixels
VIRTUAL_W = RES_W * CELL_W
VIRTUAL_H = RES_H * CELL_H
TOTAL_FRAMES = FPS * DURATION

# Output
OUT_MP4 = os.path.expanduser("~/.hermes/cron/output/stellar_flow.mp4")
OUT_GIF = os.path.expanduser("~/.hermes/cron/output/stellar_flow.gif")
os.makedirs(os.path.dirname(OUT_MP4), exist_ok=True)

# ─── PALETTES ────────────────────────────────────────────────────────────────
# Aurora-inspired palette: deep space → teal → green → purple → pink
AURORA_PALETTE = [
    (0.55, 0.82, 1.00),  # ice blue
    (0.20, 0.90, 0.75),  # teal glow
    (0.30, 0.95, 0.50),  # aurora green
    (0.55, 0.75, 1.00),  # soft violet
    (0.90, 0.55, 0.85),  # pink nebula
    (1.00, 0.75, 0.40),  # warm gold
]

def hsv_to_rgb(h, s, v):
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    RGB = [(v, t, p), (q, v, p), (p, v, t), (p, t, v), (t, p, v), (v, p, q)]
    return tuple(int(x * 255) for x in RGB[i])

# Character sets — density ramps
DENSE     = "█▓▒░ "
MEDIUM    = "▓▒░·∙"
SPARSE    = "░·∙∘○"
STARS     = "·∙∘○◦°"
RAINBOW   = "▀▄▌▐█▓▒░"

# ─── FONTS ───────────────────────────────────────────────────────────────────
import textwrap
import shutil

FONT_PATH = "/system/fonts/DroidSansMono.ttf"

# ─── NUMPY SEEDED RNG ─────────────────────────────────────────────────────────
rng = np.random.default_rng(42)

# ─── PRE-BUILD PARTICLES ─────────────────────────────────────────────────────
N_PARTICLES = 280
particles = {
    'x': rng.uniform(0, RES_W, N_PARTICLES),
    'y': rng.uniform(0, RES_H, N_PARTICLES),
    'vx': rng.uniform(-0.08, 0.08, N_PARTICLES),
    'vy': rng.uniform(-0.15, -0.02, N_PARTICLES),
    'life': rng.uniform(0, 1, N_PARTICLES),
    'size': rng.uniform(0.5, 2.0, N_PARTICLES),
    'hue': rng.uniform(0, 1, N_PARTICLES),
}

# ─── EFFECT BUILDERS ──────────────────────────────────────────────────────────

def wave_field(x, y, t, freq=3.0, phase=0.0):
    """Sine wave interference field"""
    return 0.5 + 0.5 * sin(sqrt(x*x + y*y) * freq * 0.15 - t * 2.0 + phase)

def aurora_bands(y, t, speed=1.2):
    """Horizontal aurora curtain bands"""
    band1 = sin(y * 0.4 + t * speed) * 0.5 + 0.5
    band2 = sin(y * 0.25 - t * speed * 0.7 + 1.5) * 0.3 + 0.7
    return (band1 * 0.6 + band2 * 0.4)

def fractal_noise(x, y, t, octaves=4):
    """Layered fBM noise for organic texture"""
    val = 0.0
    amp = 0.5
    freq = 1.0
    for _ in range(octaves):
        nx = x * freq * 0.05
        ny = y * freq * 0.05
        val += amp * sin(sqrt(nx*nx + ny*ny) * 3.0 + t + randint(0, 1000) * 0.01)
        amp *= 0.5
        freq *= 2.0
    return (val + 1.0) * 0.25

def plasma_blob(x, y, t, cx, cy, radius=0.3):
    """Blobby plasma field centered at (cx, cy)"""
    dist = sqrt((x - cx)**2 + (y - cy)**2)
    return (sin(dist * 8.0 - t * 3.0) + 1.0) * 0.25

# ─── TONEMAP ─────────────────────────────────────────────────────────────────
def tonemap(canvas, gamma=0.78):
    """Adaptive percentile-based brightness normalization"""
    f = canvas.astype(np.float32)
    lo, hi = np.percentile(f[::4, ::4], [2, 99.5])
    if hi - lo < 12:
        hi = lo + 12
    f = np.clip((f - lo) / (hi - lo), 0, 1) ** gamma
    return (f * 255).astype(np.uint8)

# ─── SCENE FUNCTIONS ──────────────────────────────────────────────────────────

def scene_cosmic_start(t, canvas, dt):
    """Opening: deep space with stars emerging"""
    progress = min(1.0, t / 2.0)  # 0→1 over 2 seconds
    decay = max(0, 1.0 - (t - 2.0) / 0.5) if t > 2.0 else 1.0

    # Stars fade in
    star_mask = (particles['life'] < progress * 0.8 + 0.2) & (particles['life'] > 0.05)
    for i in range(N_PARTICLES):
        if not star_mask[i]:
            continue
        px = int(particles['x'][i] * RES_W) % RES_W
        py = int(particles['y'][i] * RES_H) % RES_H
        if 0 <= px < RES_W and 0 <= py < RES_H:
            hue = particles['hue'][i]
            brightness = particles['life'][i] * progress * decay
            col = hsv_to_rgb(hue, 0.3, brightness)
            canvas[py, px] = col

    # Central glow emerges
    cx, cy = RES_W // 2, RES_H // 2
    for dy in range(-8, 9):
        for dx in range(-16, 17):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < RES_W and 0 <= ny < RES_H:
                dist = sqrt(dx*dx*0.5 + dy*dy) / 16.0
                if dist < 1.0:
                    glow = (1.0 - dist) * progress * decay * 0.6
                    r = min(255, canvas[ny, nx][0] + int(glow * 180))
                    g = min(255, canvas[ny, nx][1] + int(glow * 100))
                    b = min(255, canvas[ny, nx][2] + int(glow * 255))
                    canvas[ny, nx] = (r, g, b)

def scene_aurora_curtains(t, canvas):
    """Main: flowing aurora curtains across the sky"""
    for y in range(RES_H):
        for x in range(RES_W):
            # Multiple wave layers
            w1 = wave_field(x, y, t, freq=2.5, phase=0.0)
            w2 = wave_field(x * 1.3, y * 0.8, t, freq=3.5, phase=2.1)
            w3 = fractal_noise(x, y, t)
            aur = aurora_bands(y, t, speed=1.5)
            intensity = (w1 * 0.35 + w2 * 0.35 + w3 * 0.3) * aur

            if intensity > 0.15:
                hue = (x / RES_W * 0.3 + t * 0.08) % 1.0
                sat = 0.7 + intensity * 0.3
                val = min(1.0, intensity * 1.8)
                col = hsv_to_rgb(hue, sat, val)
                alpha = min(1.0, intensity * 2.5)
                canvas[y, x] = (
                    int(canvas[y, x][0] * (1 - alpha) + col[0] * alpha),
                    int(canvas[y, x][1] * (1 - alpha) + col[1] * alpha),
                    int(canvas[y, x][2] * (1 - alpha) + col[2] * alpha),
                )

def scene_nebula_clouds(t, canvas, dt):
    """Nebula clouds: slow-moving plasma blobs"""
    cx1 = 0.3 + 0.1 * sin(t * 0.3)
    cy1 = 0.4 + 0.1 * cos(t * 0.25)
    cx2 = 0.7 + 0.1 * cos(t * 0.2 + 1.0)
    cy2 = 0.6 + 0.1 * sin(t * 0.35 + 2.0)

    for y in range(RES_H):
        for x in range(RES_W):
            nx, ny = x / RES_W, y / RES_H
            p1 = plasma_blob(nx, ny, t, cx1, cy1)
            p2 = plasma_blob(nx, ny, t * 0.7, cx2, cy2, radius=0.4)
            nebula = p1 * 0.6 + p2 * 0.4

            if nebula > 0.1:
                hue = (nx * 0.4 + ny * 0.3 + t * 0.05) % 1.0
                if nebula > 0.4:
                    hue = (hue + 0.5) % 1.0  # Shift for highlights
                col = hsv_to_rgb(hue, 0.8, min(1.0, nebula * 1.5))
                alpha = min(0.7, nebula)
                canvas[y, x] = (
                    int(canvas[y, x][0] * (1 - alpha) + col[0] * alpha),
                    int(canvas[y, x][1] * (1 - alpha) + col[1] * alpha),
                    int(canvas[y, x][2] * (1 - alpha) + col[2] * alpha),
                )

def scene_particle_flow(t, canvas, dt):
    """Falling star particles with trails"""
    for i in range(N_PARTICLES):
        px = particles['x'][i]
        py = particles['y'][i]

        # Update position
        particles['x'][i] += particles['vx'][i]
        particles['y'][i] += particles['vy'][i]
        particles['life'][i] -= dt * 0.12

        # Wrap/respawn
        if particles['life'][i] <= 0 or particles['y'][i] < 0:
            particles['x'][i] = rng.uniform(0, 1)
            particles['y'][i] = rng.uniform(0.9, 1.1)
            particles['vx'][i] = rng.uniform(-0.03, 0.03)
            particles['vy'][i] = rng.uniform(-0.12, -0.04)
            particles['life'][i] = rng.uniform(0.4, 1.0)
            particles['hue'][i] = rng.uniform(0, 1)
            px = particles['x'][i]
            py = particles['y'][i]

        # Draw particle with glow
        gx = int(px * RES_W) % RES_W
        gy = int(py * RES_H) % RES_H
        if 0 <= gx < RES_W and 0 <= gy < RES_H:
            life = particles['life'][i]
            hue = particles['hue'][i]
            col = hsv_to_rgb(hue, 0.5, life)
            canvas[gy, gx] = col

            # Trail
            trail_len = int(4 * life)
            for tr in range(1, trail_len + 1):
                tx = int((px + particles['vx'][i] * tr * 2) * RES_W) % RES_W
                ty = int((py + particles['vy'][i] * tr * 2) * RES_H) % RES_H
                if 0 <= tx < RES_W and 0 <= ty < RES_H:
                    trail_alpha = life * (1.0 - tr / trail_len) * 0.4
                    trail_col = hsv_to_rgb(hue, 0.6, trail_alpha)
                    canvas[ty, tx] = (
                        int(canvas[ty, tx][0] * (1 - trail_alpha) + trail_col[0] * trail_alpha),
                        int(canvas[ty, tx][1] * (1 - trail_alpha) + trail_col[1] * trail_alpha),
                        int(canvas[ty, tx][2] * (1 - trail_alpha) + trail_col[2] * trail_alpha),
                    )

def scene_cosmic_outro(t, canvas, dt):
    """Outro: everything dissolves into starfield"""
    # Reverse fade - stars remain but aurora fades
    fade = max(0, 1.0 - (t - 6.0) / 2.0) if t > 6.0 else 1.0
    fade_factor = 1.0 - fade * 0.05
    for c in range(3):
        canvas[:, :, c] = np.clip(canvas[:, :, c] * fade_factor, 0, 255).astype(np.uint8)

# ─── RENDER PIPELINE ─────────────────────────────────────────────────────────

def render_frame(t, dt):
    """Render a single frame at time t"""
    canvas = np.zeros((RES_H, RES_W, 3), dtype=np.uint8)

    if t < 3.0:
        scene_cosmic_start(t, canvas, dt)
        scene_aurora_curtains(t, canvas)
    elif t < 5.5:
        scene_aurora_curtains(t, canvas)
        scene_nebula_clouds(t, canvas, dt)
        scene_particle_flow(t, canvas, dt)
    else:
        scene_nebula_clouds(t, canvas, dt)
        scene_particle_flow(t, canvas, dt)
        scene_cosmic_outro(t, canvas, dt)

    return tonemap(canvas, gamma=0.78)

# ─── ASCII ENCODING ───────────────────────────────────────────────────────────

def render_ascii_frame(canvas):
    """Convert RGB canvas to ASCII art string with ANSI colors"""
    lines = []
    for y in range(RES_H):
        line_chars = []
        for x in range(RES_W):
            r, g, b = canvas[y, x]
            brightness = (r * 0.299 + g * 0.587 + b * 0.114) / 255.0

            # Choose character by brightness
            if brightness > 0.85:
                ch = "█"
            elif brightness > 0.65:
                ch = "▓"
            elif brightness > 0.45:
                ch = "▒"
            elif brightness > 0.25:
                ch = "░"
            else:
                ch = " "

            # Color: map RGB to 256-color ANSI
            ansi_r = (r // 32) * 36
            ansi_g = (g // 32) * 36
            ansi_b = (b // 32) * 36
            ansi_color = 16 + ansi_r + ansi_g + ansi_b

            line_chars.append(f"\033[38;5;{ansi_color}m{ch}")
        lines.append("".join(line_chars))
    return "\n".join(lines) + "\033[0m"

def render_frame_to_image(canvas, frame_num):
    """Render canvas to PNG via Pillow"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    img = Image.new("RGB", (RES_W * 6, RES_H * 12), (0, 0, 0))
    draw = ImageDraw.Draw(img)

    font = None
    if FONT_PATH and os.path.exists(FONT_PATH):
        try:
            font = ImageFont.truetype(FONT_PATH, 11)
        except Exception:
            font = ImageFont.load_default()
    else:
        font = ImageFont.load_default()

    for y in range(RES_H):
        for x in range(RES_W):
            r, g, b = canvas[y, x]
            brightness = (r * 0.299 + g * 0.587 + b * 0.114) / 255.0

            if brightness > 0.85:
                ch = "█"
            elif brightness > 0.65:
                ch = "▓"
            elif brightness > 0.45:
                ch = "▒"
            elif brightness > 0.25:
                ch = "░"
            else:
                ch = " "

            draw.text((x * 6, y * 12), ch, fill=(r, g, b), font=font)

    return img

# ─── FFMPEG ENCODING ──────────────────────────────────────────────────────────

def encode_video_png_sequence():
    """Render all frames as PNGs and encode with ffmpeg"""
    print(f"Rendering {TOTAL_FRAMES} frames...")

    # Create temp dir for frames
    frame_dir = os.path.expanduser("~/.hermes/cron/output/frames_stellar")
    os.makedirs(frame_dir, exist_ok=True)

    frames = []
    for frame_num in range(TOTAL_FRAMES):
        t = frame_num / FPS
        dt = 1.0 / FPS
        canvas = render_frame(t, dt)

        img = render_frame_to_image(canvas, frame_num)
        if img:
            frame_path = os.path.join(frame_dir, f"frame_{frame_num:04d}.png")
            img.save(frame_path)
            frames.append(frame_path)

        if frame_num % 12 == 0:
            print(f"  Frame {frame_num}/{TOTAL_FRAMES} ({frame_num*100//TOTAL_FRAMES}%)")

    # Encode MP4
    print("Encoding MP4...")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frame_dir, "frame_%04d.png"),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-vf", f"scale={VIRTUAL_W}:{VIRTUAL_H}",
        OUT_MP4
    ]
    result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg MP4 error: {result.stderr[-500:]}")
    else:
        print(f"✓ MP4 saved: {OUT_MP4}")

    # Encode GIF
    print("Encoding GIF...")
    gif_cmd = [
        "ffmpeg", "-y",
        "-framerate", "15",
        "-i", os.path.join(frame_dir, "frame_%04d.png"),
        "-vf", f"fps=15,scale={RES_W*4}:{RES_H*8}:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
        OUT_GIF
    ]
    result = subprocess.run(gif_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg GIF error: {result.stderr[-500:]}")
    else:
        print(f"✓ GIF saved: {OUT_GIF}")

    # Cleanup frames
    import shutil
    shutil.rmtree(frame_dir, ignore_errors=True)
    print("Done!")

    return OUT_MP4, OUT_GIF

# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("  ✦ 星际流光 / STELLAR FLOW ✦")
    print("  Cosmic Aurora ASCII Art Video Generator")
    print("=" * 50)
    print(f"  Resolution: {RES_W}×{RES_H} chars")
    print(f"  Duration: {DURATION}s @ {FPS}fps = {TOTAL_FRAMES} frames")
    print(f"  Output: {OUT_MP4}")
    print()

    mp4_out, gif_out = encode_video_png_sequence()
    print(f"\n✓ Complete!")
    print(f"  MP4: {mp4_out}")
    print(f"  GIF: {gif_out}")
