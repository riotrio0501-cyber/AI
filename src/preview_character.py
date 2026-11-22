"""全表情を並べたプレビューPNGを output/ に出す。

使い方: python src/preview_character.py taro hana
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from character import Character, FACES, ROOT  # noqa: E402

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def main(names):
    cols = [(f, dict(face=f)) for f in FACES] + [
        ("blink", dict(face="normal", blink=True)),
        ("talk 半", dict(face="normal", mouth=1)),
        ("talk 全", dict(face="normal", mouth=2)),
        ("angry 全", dict(face="angry", mouth=2, arm_l=-25, arm_r=25)),
        ("smile 全", dict(face="smile", mouth=2)),
    ]
    scale = 0.4
    cw, ch = int(600 * scale), int(1000 * scale)
    pad, label = 16, 40
    sheet = Image.new("RGB", (pad + len(cols) * (cw + pad), pad + len(names) * (ch + label + pad)), "#F4F1EA")
    d = ImageDraw.Draw(sheet)
    for r, n in enumerate(names):
        ch_ = Character(n, scale)
        y = pad + r * (ch + label + pad)
        for c, (title, kw) in enumerate(cols):
            x = pad + c * (cw + pad)
            d.rounded_rectangle([x, y, x + cw, y + ch + label], 12, fill="#FFFFFF")
            sheet.paste(ch_.render(**kw), (x, y + label), ch_.render(**kw))
            d.text((x + 10, y + 6), f"{ch_.cfg['display_name']} / {title}", fill="#333", font=font(20))
    out = ROOT / "output" / "preview_characters.png"
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:] or ["taro", "hana"])
