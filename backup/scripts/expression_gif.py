#!/usr/bin/env python3
"""
嘟嘴 → 微笑 像素表情动画
Expression: Pout → Smile
"""

import subprocess
import sys
import os

# ─── CONFIG ──────────────────────────────────────────────────────────────────
FPS = 8
DURATION = 2.0          # 2秒动画
TOTAL_FRAMES = int(FPS * DURATION)  # 16 frames

OUT_GIF = os.path.expanduser("~/.hermes/cron/output/emotion_pout_to_smile.gif")
OUT_APNG = os.path.expanduser("~/.hermes/cron/output/emotion_pout_to_smile.png")
os.makedirs(os.path.dirname(OUT_GIF), exist_ok=True)

# ─── PIXEL FACE TEMPLATE ─────────────────────────────────────────────────────
# Face size: 32×32 pixels, rendered as colored blocks
# Each "pixel" will be a small filled rectangle in the output image

FACE_W = 32
FACE_H = 32
PIXEL_SIZE = 16   # each pixel = 16x16 screen pixels → 512x512 output
OUTPUT_SIZE = FACE_W * PIXEL_SIZE  # 512x512

# ─── FACE DRAWING RULES ──────────────────────────────────────────────────────
# The face grid uses codes:
#   0 = transparent/skin
#   1 = face outline / skin
#   2 = cheek blush
#   3 = eye
#   4 = eyebrow
#   5 = mouth (pout = 5, smile = 6, transition = varies)
#   7 = highlight

def draw_face_grid(expression_value):
    """
    expression_value: 0.0 (pout) → 1.0 (smile)
    Returns a FACE_H × FACE_W grid of color tuples (r,g,b,a)
    """
    # Base skin color
    SKIN = (255, 220, 177, 255)
    SKIN_SHADOW = (235, 190, 145, 255)
    OUTLINE = (180, 130, 90, 255)
    CHEEK = (255, 150, 150, 100)  # semi-transparent blush
    EYE = (60, 40, 30, 255)
    EYE_HL = (255, 255, 255, 220)
    EYEBROW = (80, 50, 30, 255)
    LIP_BASE = (200, 80, 80, 255)
    LIP_LIGHT = (220, 120, 120, 255)
    LIP_DARK = (160, 50, 50, 255)
    WHITE = (255, 255, 255, 255)

    grid = [[None] * FACE_W for _ in range(FACE_H)]

    def set_grid(y, x, color):
        if 0 <= y < FACE_H and 0 <= x < FACE_W:
            grid[y][x] = color

    def fill(y, x, h, w, color):
        for dy in range(h):
            for dx in range(w):
                set_grid(y + dy, x + dx, color)

    # ─── Face outline (oval) ─────────────────────────────────────────────────
    # Center at (16, 16), radii: rx=14, ry=15
    for y in range(FACE_H):
        for x in range(FACE_W):
            dx = (x - 16) / 14.0
            dy = (y - 16) / 15.0
            d2 = dx*dx + dy*dy
            if d2 <= 1.0:
                # gradient skin: slightly darker at edges
                brightness = 1.0 - d2 * 0.08
                r = int(SKIN[0] * brightness)
                g = int(SKIN[1] * brightness)
                b = int(SKIN[2] * brightness)
                grid[y][x] = (r, g, b, 255)

    # ─── Face outline stroke ─────────────────────────────────────────────────
    outline_pixels = []
    for y in range(FACE_H):
        for x in range(FACE_W):
            dx = (x - 16) / 14.0
            dy = (y - 16) / 15.0
            d2 = dx*dx + dy*dy
            if 0.92 <= d2 <= 1.08:
                outline_pixels.append((y, x))

    # ─── Hair / top ──────────────────────────────────────────────────────────
    hair_row = 4
    for x in range(6, 26):
        set_grid(hair_row, x, (60, 40, 25, 255))
    for x in range(5, 27):
        set_grid(hair_row + 1, x, (55, 35, 22, 255))
    for x in range(4, 28):
        set_grid(hair_row + 2, x, (50, 30, 20, 255))
    # Side hair
    for y in range(5, 14):
        set_grid(y, 4, (50, 30, 20, 255))
        set_grid(y, 27, (50, 30, 20, 255))
        set_grid(y, 5, (55, 35, 22, 255))
        set_grid(y, 26, (55, 35, 22, 255))

    # ─── Eyebrows ────────────────────────────────────────────────────────────
    # Left eyebrow: y≈10, x from 9 to 13
    ev = expression_value  # 0=pout (arched/sad) → 1=smile (raised/happy)
    brow_lift = int(ev * 1.5)  # brows raise slightly when smiling
    brow_furrow = int((1.0 - ev) * 1.0)  # more furrowed when pouting
    for x in range(9, 14):
        y = 10 - brow_lift + (1 if x in [9, 13] else 0)
        set_grid(y, x, EYEBROW)
        if brow_furrow > 0:
            set_grid(y + 1, x, EYEBROW)
    # Right eyebrow
    for x in range(18, 23):
        y = 10 - brow_lift + (1 if x in [18, 22] else 0)
        set_grid(y, x, EYEBROW)
        if brow_furrow > 0:
            set_grid(y + 1, x, EYEBROW)

    # ─── Eyes ────────────────────────────────────────────────────────────────
    # Left eye center: (11, 12), right eye center: (21, 12)
    eye_y = 12 - int(ev * 0.5)  # eyes slightly up when smiling
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            d = (dx**2 + dy**2) ** 0.5
            if d <= 2.2:
                set_grid(eye_y + dy, 11 + dx, EYE)
                # Eye highlight
                if dy == -1 and dx == 1:
                    set_grid(eye_y + dy, 11 + dx, EYE_HL)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            d = (dx**2 + dy**2) ** 0.5
            if d <= 2.2:
                set_grid(eye_y + dy, 21 + dx, EYE)
                if dy == -1 and dx == 1:
                    set_grid(eye_y + dy, 21 + dx, EYE_HL)

    # Eyelashes (when happy, more visible)
    if ev > 0.3:
        set_grid(eye_y - 3, 10, EYEBROW)
        set_grid(eye_y - 3, 11, EYEBROW)
        set_grid(eye_y - 3, 12, EYEBROW)
        set_grid(eye_y - 3, 20, EYEBROW)
        set_grid(eye_y - 3, 21, EYEBROW)
        set_grid(eye_y - 3, 22, EYEBROW)

    # ─── Cheeks (blush, visible when happy) ──────────────────────────────────
    blush_intensity = int(ev * 80)
    if ev > 0.2:
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                d = (dx**2 + dy**2) ** 0.5
                if d <= 2.5:
                    y, x = 16 + dy, 6 + dx
                    existing = grid[y][x]
                    if existing:
                        r = min(255, existing[0] + blush_intensity)
                        g = max(0, existing[1] - blush_intensity // 2)
                        b = max(0, existing[2] - blush_intensity // 2)
                        set_grid(y, x, (r, g, b, 255))
                    y, x = 16 + dy, 25 + dx
                    existing = grid[y][x]
                    if existing:
                        r = min(255, existing[0] + blush_intensity)
                        g = max(0, existing[1] - blush_intensity // 2)
                        b = max(0, existing[2] - blush_intensity // 2)
                        set_grid(y, x, (r, g, b, 255))

    # ─── Mouth ───────────────────────────────────────────────────────────────
    # expression_value: 0.0 = pout (小嘴撅起), 0.5 = neutral, 1.0 = smile (咧嘴笑)
    # Mouth center: (16, 22)

    if expression_value < 0.5:
        # Pout region: small circular protruding mouth
        # The more "pouty", the more the lips protrude (darker, smaller center)
        t = expression_value / 0.5  # 0 → 1 as we go from pout to neutral
        mouth_radius = int(2.0 + t * 1.5)  # 2 → 3.5
        mouth_y = 22
        mouth_x = 16
        for dy in range(-mouth_radius, mouth_radius + 1):
            for dx in range(-mouth_radius, mouth_radius + 1):
                d = (dx**2 + dy**2) ** 0.5
                if d <= mouth_radius:
                    y, x = mouth_y + dy, mouth_x + dx
                    # Pout: lips darker, more saturated red
                    if d < mouth_radius * 0.5:
                        set_grid(y, x, LIP_DARK)
                    elif d < mouth_radius * 0.8:
                        set_grid(y, x, LIP_BASE)
                    else:
                        set_grid(y, x, LIP_LIGHT)
        # Pout protrusion effect: darken center to make it look raised
        center_dark = int((1.0 - expression_value / 0.5) * 40)
        if center_dark > 0:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    y, x = mouth_y + dy, mouth_x + dx
                    existing = grid[y][x]
                    if existing:
                        set_grid(y, x, (
                            max(0, existing[0] - center_dark),
                            max(0, existing[1] - center_dark // 2),
                            max(0, existing[2] - center_dark // 3),
                            255
                        ))

    else:
        # Smile region: arc mouth, wider as expression_value → 1.0
        t = (expression_value - 0.5) / 0.5  # 0 → 1 as we go from neutral to big smile
        # Mouth arc: from left corner to right corner, curving down
        mouth_width = int(5 + t * 5)   # 5 → 10 wide
        mouth_depth = int(2 + t * 4)   # 2 → 6 deep (how open)
        mouth_y_base = 22
        mouth_x_base = 16

        for x in range(-mouth_width, mouth_width + 1):
            # Arc equation: y = depth * (1 - (x/w)^2)
            frac = abs(x) / max(1, mouth_width)
            depth = int(mouth_depth * (1.0 - frac * frac))
            for dy in range(depth + 1):
                y = mouth_y_base + dy
                # Inside mouth: dark red
                if dy >= depth - 1 and dy <= depth:
                    # Lip border
                    set_grid(y, mouth_x_base + x, LIP_LIGHT)
                else:
                    # Inside
                    set_grid(y, mouth_x_base + x, LIP_BASE if dy < depth - 1 else LIP_LIGHT)

        # Corner dimples when very happy
        if expression_value > 0.75:
            set_grid(mouth_y_base, mouth_x_base - mouth_width, LIP_DARK)
            set_grid(mouth_y_base, mouth_x_base + mouth_width, LIP_DARK)

    return grid

# ─── RENDER GRID TO IMAGE ────────────────────────────────────────────────────

def render_grid_to_png(grid, output_path):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False

    img = Image.new("RGBA", (OUTPUT_SIZE, OUTPUT_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(FACE_H):
        for x in range(FACE_W):
            color = grid[y][x]
            if color is None:
                continue
            # Draw pixel as PIXEL_SIZE×PIXEL_SIZE square
            px = x * PIXEL_SIZE
            py = y * PIXEL_SIZE
            draw.rectangle([px, py, px + PIXEL_SIZE - 1, py + PIXEL_SIZE - 1], fill=color)

    img.save(output_path, "PNG")
    return True

# ─── GENERATE FRAMES ────────────────────────────────────────────────────────

print(f"Generating {TOTAL_FRAMES} frames...")

frame_dir = os.path.expanduser("~/.hermes/cron/output/emo_frames")
os.makedirs(frame_dir, exist_ok=True)

frame_paths = []
for i in range(TOTAL_FRAMES):
    t = i / (TOTAL_FRAMES - 1)  # 0.0 → 1.0
    grid = draw_face_grid(t)
    frame_path = os.path.join(frame_dir, f"frame_{i:03d}.png")
    if render_grid_to_png(grid, frame_path):
        frame_paths.append(frame_path)
    if i % 4 == 0:
        print(f"  Frame {i}/{TOTAL_FRAMES} (pout={1.0-t:.2f} → smile={t:.2f})")

print(f"Encoding GIF...")

# Build ffmpeg palette for high quality GIF
palette_cmd = [
    "ffmpeg", "-y",
    "-framerate", str(FPS),
]
for fp in frame_paths:
    palette_cmd.extend(["-i", fp])

# First pass: generate palette
palette_file = os.path.join(frame_dir, "palette.png")
pass1_cmd = palette_cmd + [
    "-vf", f"fps={FPS},scale=512:512:flags=lanczos,palettegen=stats_mode=diff",
    palette_file
]
r = subprocess.run(pass1_cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(f"Palette error: {r.stderr[-300:]}")
else:
    print("Palette generated.")

# Second pass: encode GIF using palette
pass2_cmd = ["ffmpeg", "-y", "-framerate", str(FPS), "-i", frame_dir + "/frame_%03d.png",
             "-i", palette_file,
             "-lavfi", f"fps={FPS},scale=512:512:flags=lanczos[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=3",
             OUT_GIF]
r = subprocess.run(pass2_cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(f"GIF error: {r.stderr[-300:]}")
else:
    print(f"✓ GIF: {OUT_GIF}")

# Also save as animated PNG (APNG) for better quality
apng_cmd = ["ffmpeg", "-y", "-framerate", str(FPS),
            "-i", frame_dir + "/frame_%03d.png",
            "-vf", f"fps={FPS},scale=512:512:flags=lanczos",
            "-plays", "0",  # infinite loop for APNG
            OUT_APNG]
r = subprocess.run(apng_cmd, capture_output=True, text=True)
if r.returncode != 0:
    print(f"APNG error: {r.stderr[-300:]}")
else:
    print(f"✓ APNG: {OUT_APNG}")

# Cleanup
import shutil
shutil.rmtree(frame_dir, ignore_errors=True)
print("Done!")
