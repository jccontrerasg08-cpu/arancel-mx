# Small script to generate a synthetic demo GIF for README
# Creates docs/demo.gif showing example CLI commands and outputs

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    print("Pillow not installed, installing via pip...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"]) 
    from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs')
OUT_DIR = os.path.abspath(OUT_DIR)
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, 'demo.gif')

W, H = 720, 180
BG = (11, 18, 38)
FG = (205, 227, 255)
FONT = ImageFont.load_default()

lines = [
    ("arancel-mx", 28),
    ("", 18),
    ("$ python -m arancel_mx --help", 14),
    ("Usage: arancel-mx [OPTIONS] COMMAND [ARGS]...", 12),
    ("", 12),
    ("$ python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release", 14),
    ("Exporting canonical artifacts...", 12),
    ("Wrote: out/release/arancel_mx.csv", 12),
    ("Wrote: out/release/arancel_mx.json", 12),
    ("Wrote: out/release/arancel_mx.duckdb", 12),
    ("All done — demo", 12),
]

frames = []
# Create a sequence of frames that progressively reveal lines (simple animation)
for i in range(len(lines)):
    img = Image.new('RGB', (W, H), BG)
    draw = ImageDraw.Draw(img)
    y = 18
    for j in range(i + 1):
        text, size = lines[j]
        draw.text((24, y), text, font=FONT, fill=FG)
        y += 20
    frames.append(img)

# Append a few hold frames for the final state
for _ in range(6):
    frames.append(frames[-1])

frames[0].save(OUT_PATH, save_all=True, append_images=frames[1:], duration=600, loop=0)
print(f"Wrote demo GIF: {OUT_PATH}")
