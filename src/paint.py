"""手描き水彩っぽい質感をつける後処理（紙の目・色ムラ・周辺減光）。"""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageFilter


def _noise(h, w, cell, rng):
    small = rng.random((max(2, h // cell), max(2, w // cell))).astype(np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(img, np.float32) / 255.0 - 0.5


@lru_cache(maxsize=4)
def texture(w=1080, h=1920, seed=7):
    """乗算用のテクスチャ（HxWx3, 1.0中心）。"""
    rng = np.random.default_rng(seed)
    blot = _noise(h, w, 90, rng) * 0.045 + _noise(h, w, 30, rng) * 0.025   # 色ムラ
    grain = (rng.random((h, w)).astype(np.float32) - 0.5) * 0.035        # 紙の目
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w * 0.75)) ** 2 + ((yy - h / 2) / (h * 0.75)) ** 2)
    vig = 1.0 - np.clip(r - 0.45, 0, 1) * 0.35                           # 周辺減光
    t = (1.0 + blot + grain) * vig
    warm = np.array([1.0, 0.985, 0.95], np.float32)                      # ほんのり暖色
    return t[..., None] * warm


def paint(img: Image.Image, strength=1.0, soften=True) -> Image.Image:
    """RGB画像に水彩の質感をかける。"""
    rgb = img.convert("RGB")
    if soften:
        rgb = rgb.filter(ImageFilter.GaussianBlur(1.0))
    a = np.asarray(rgb, np.float32)
    t = texture(rgb.width, rgb.height)
    t = 1.0 + (t - 1.0) * strength
    return Image.fromarray(np.clip(a * t, 0, 255).astype(np.uint8))
