"""キャラのSVGパーツを読み込み、表情・口・腕角度を指定して1枚のRGBA画像に合成する。"""
from functools import lru_cache
from pathlib import Path

import cairosvg
import yaml
from io import BytesIO
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FACES = ["normal", "surprised", "angry", "troubled", "smile"]
ARM_PIVOT = {"arm_l": (222, 590), "arm_r": (378, 590)}
CANVAS = (600, 1000)


class Character:
    def __init__(self, name: str, scale: float = 1.0):
        self.name = name
        self.dir = ROOT / "characters" / name
        self.cfg = yaml.safe_load((self.dir / "character.yaml").read_text(encoding="utf-8"))
        self.scale = scale
        if not (self.dir / "parts" / "body.svg").exists():
            from make_character import build
            build(name)

    @property
    def size(self):
        return int(CANVAS[0] * self.scale), int(CANVAS[1] * self.scale)

    @lru_cache(maxsize=None)
    def part(self, fname: str) -> Image.Image:
        data = (self.dir / "parts" / f"{fname}.svg").read_bytes()
        w, h = self.size
        png = cairosvg.svg2png(bytestring=data, output_width=w, output_height=h)
        return Image.open(BytesIO(png)).convert("RGBA")

    def _arm(self, side: str, angle: float) -> Image.Image:
        img = self.part(side)
        if abs(angle) < 0.01:
            return img
        px, py = ARM_PIVOT[side]
        return img.rotate(angle, resample=Image.BICUBIC,
                          center=(px * self.scale, py * self.scale))

    def render(self, face="normal", mouth=0, blink=False, arm_l=0.0, arm_r=0.0) -> Image.Image:
        """face: 表情 / mouth: 0閉 1半 2全開 / arm_*: 腕の回転角(度, 反時計回り正)"""
        if face not in FACES:
            face = "normal"
        eyes = "closed" if blink and face != "smile" else face
        out = Image.new("RGBA", self.size, (0, 0, 0, 0))
        for layer in [self.part("hair_back"), self.part("body"),
                      self._arm("arm_l", arm_l), self._arm("arm_r", arm_r),
                      self.part("head"), self.part(f"eyes_{eyes}"),
                      self.part(f"brows_{face}"), self.part(f"mouth_{face}_{mouth}"),
                      self.part("hair_front")]:
            out.alpha_composite(layer)
        return out
