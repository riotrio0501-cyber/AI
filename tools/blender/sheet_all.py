"""3人の並び（大きさ比べ）＋各キャラの正面・ななめを書き出す。

使い方: python3 tools/blender/sheet_all.py [--preview]
→ assets/characters/lineup_3d.png ほか
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bpy  # noqa: E402

from characters import build_don, build_goro, build_pipi  # noqa: E402
from lib import camera, lights, render_settings, render_still, reset, snow_ground, world_sky  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "assets" / "characters"
preview = "--preview" in sys.argv

reset()
world_sky()
snow_ground()
lights()
goro = build_goro((-1.2, 0, 0))
don = build_don((0.4, 0.6, 0))
pipi = build_pipi((1.9, -0.2, 0))
for ob, deg in ((goro, 15), (don, -5), (pipi, -20)):
    ob.rotation_euler.z = math.radians(deg)
sc = render_settings(samples=24 if preview else 64, preview=preview)
sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
camera(loc=(0.3, -7.5, 1.6), target=(0.3, 0, 1.2), lens=40)
render_still(OUT / "lineup_3d.png")
print("saved")
