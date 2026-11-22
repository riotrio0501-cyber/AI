"""背景＋キャラを1080x1920で合成したスタイル見本を output/ に出す。"""
import sys
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character import Character, ROOT  # noqa: E402
from paint import paint  # noqa: E402


def load_bg(name):
    png = cairosvg.svg2png(url=str(ROOT / "backgrounds" / f"{name}.svg"), output_width=1080, output_height=1920)
    return paint(Image.open(BytesIO(png)), strength=1.0)


bg = load_bg("kitchen").convert("RGBA")
for name, x, kw in [("hana", 70, dict(face="angry", mouth=2, arm_l=-20, arm_r=20)),
                    ("taro", 520, dict(face="troubled"))]:
    c = Character(name, 0.8)
    bg.alpha_composite(c.render(**kw), (x, 760))
out = paint(bg, strength=0.5, soften=False)
path = ROOT / "output" / "style_sample.png"
out.save(path)
print(path)
