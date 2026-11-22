"""キャラ1人の設定画（正面・ななめ・横・後ろ）を書き出す。

使い方: python3 tools/blender/sheet.py goro|pipi|don [--preview]
→ assets/characters/<名前>_3d_sheet.png
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

import characters  # noqa: E402
from lib import camera, lights, render_settings, render_still, reset, snow_ground, world_sky  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "assets" / "characters"
who = sys.argv[1]
preview = "--preview" in sys.argv
# キャラごとのカメラ（距離, 注視点の高さ）
FRAMING = {"goro": (3.2, 0.5), "pipi": (2.8, 0.45), "don": (8.5, 1.55)}

reset()
world_sky()
snow_ground()
lights()
ch = getattr(characters, f"build_{who}")()
dist, zc = FRAMING[who]
camera(loc=(0, -dist, zc + dist * 0.12), target=(0, 0, zc), lens=55)
sc = render_settings(samples=24 if preview else 64, preview=preview)
sc.render.resolution_x, sc.render.resolution_y = 1080, 1080

paths = []
for name, deg in {"front": 0, "three_quarter": 35, "side": 90, "back": 180}.items():
    ch.rotation_euler = (0, 0, math.radians(deg))
    p = OUT / f".{who}_{name}.png"
    render_still(p)
    paths.append(p)

from PIL import Image  # noqa: E402

ims = [Image.open(p) for p in paths]
w, h = ims[0].size
sheet = Image.new("RGB", (w * 2, h * 2))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % 2) * w, (i // 2) * h))
sheet.save(OUT / f"{who}_3d_sheet.png")
for p in paths:
    p.unlink()
print("saved", who)
