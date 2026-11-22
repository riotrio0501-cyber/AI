"""仮素材を作る：キャラの仮立ち絵（口閉じ/口開け）、仮背景、自作の効果音・BGM。
既にファイルがあるものは上書きしない（本番素材を守るため）。 --force で作り直し。
使い方: python3 tools/make_placeholders.py
"""
import json, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FORCE = "--force" in sys.argv
SR = 48000


def need(p: Path) -> bool:
    p.parent.mkdir(parents=True, exist_ok=True)
    return FORCE or not p.exists()


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------- キャラの仮立ち絵 ----------
def make_character(name, color):
    W, H = 560, 760
    rgb = hex2rgb(color)
    for state in ("close", "open"):
        out = ROOT / "assets/characters" / name / f"{state}.png"
        if not need(out):
            continue
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        # 体（服）
        d.rounded_rectangle([40, 430, W - 40, H + 40], radius=120, fill=rgb + (255,), outline=(30, 30, 30, 255), width=6)
        # 顔
        d.ellipse([130, 90, 430, 450], fill=(255, 228, 205, 255), outline=(30, 30, 30, 255), width=6)
        # 目
        for cx in (220, 340):
            d.ellipse([cx - 18, 230, cx + 18, 272], fill=(40, 40, 40, 255))
        # 口
        if state == "close":
            d.line([250, 360, 310, 360], fill=(120, 40, 40, 255), width=8)
        else:
            d.ellipse([245, 335, 315, 400], fill=(150, 30, 40, 255), outline=(60, 20, 20, 255), width=4)
        # 名前
        f = ImageFont.truetype(FONT, 90)
        tw = d.textlength(name, font=f)
        d.text(((W - tw) / 2, 540), name, font=f, fill=(255, 255, 255, 255), stroke_width=6, stroke_fill=(30, 30, 30, 255))
        f2 = ImageFont.truetype(FONT, 34)
        d.text((W / 2 - d.textlength("（仮）", font=f2) / 2, 660), "（仮）", font=f2, fill=(255, 255, 255, 230))
        im.save(out)


# ---------- 仮背景（和室の居間っぽい図形） ----------
def make_background():
    out = ROOT / "assets/backgrounds/living.png"
    if not need(out):
        return
    W, H = 1080, 1920
    im = Image.new("RGB", (W, H), (236, 222, 190))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 420], fill=(120, 90, 60))           # 天井
    d.rectangle([0, 1250, W, H], fill=(196, 186, 120))         # 畳
    for x in range(0, W, 270):
        d.line([x, 1250, x, H], fill=(150, 140, 90), width=6)
    for y in (1500, 1750):
        d.line([0, y, W, y], fill=(150, 140, 90), width=6)
    d.rectangle([140, 520, 940, 1000], fill=(250, 246, 232), outline=(110, 80, 50), width=14)  # 障子
    for x in range(140, 941, 160):
        d.line([x, 520, x, 1000], fill=(110, 80, 50), width=6)
    for y in range(520, 1001, 120):
        d.line([140, y, 940, y], fill=(110, 80, 50), width=6)
    d.rectangle([300, 1150, 780, 1250], fill=(110, 70, 40))     # ちゃぶ台
    f = ImageFont.truetype(FONT, 40)
    d.text((40, 440), "背景（仮）：山形の実家の居間", font=f, fill=(110, 80, 50))
    im.save(out)


# ---------- 自作の効果音・BGM（合成音なので権利の心配なし） ----------
def save_wav(path, x):
    x = np.clip(x, -1, 1)
    st = np.stack([x, x], 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def env(n, a=0.005, r=0.3):
    t = np.arange(n) / SR
    return np.minimum(t / a, 1) * np.exp(-t / r)


def tone(f, dur, kind="sine"):
    t = np.arange(int(dur * SR)) / SR
    ph = 2 * np.pi * f * t
    if kind == "square":
        return np.sign(np.sin(ph)) * 0.5
    if kind == "tri":
        return 2 / np.pi * np.arcsin(np.sin(ph))
    return np.sin(ph)


def make_sounds():
    rng = np.random.default_rng(0)
    p = ROOT / "assets/se/don.wav"          # ドン！（低い衝撃音）
    if need(p):
        n = int(0.9 * SR); t = np.arange(n) / SR
        f = 40 + 110 * np.exp(-t / 0.08)
        x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.35)
        x += rng.normal(0, 1, n) * np.exp(-t / 0.02) * 0.4
        save_wav(p, x * 0.9)
    p = ROOT / "assets/se/shock.wav"        # ガーン（不協和音が下がる）
    if need(p):
        n = int(1.6 * SR); t = np.arange(n) / SR
        x = sum(np.sin(2 * np.pi * np.cumsum(f0 * (1 - 0.25 * t / 1.6)) / SR) for f0 in (220, 233, 311))
        save_wav(p, x / 3 * np.exp(-t / 0.7) * np.minimum(t / 0.01, 1) * 0.8)
    p = ROOT / "assets/se/chan.wav"         # チャンチャン（オチ）
    if need(p):
        a = (tone(784, 0.18, "square") + tone(1047, 0.18, "square")) * env(int(0.18 * SR), r=0.1)
        b = (tone(784, 0.5, "square") + tone(1047, 0.5, "square")) * env(int(0.5 * SR), r=0.2)
        save_wav(p, np.concatenate([a, np.zeros(int(0.07 * SR)), b]) * 0.35)
    p = ROOT / "assets/se/notify.wav"       # 通知音（ポロン）※既存アプリの音は使わない
    if need(p):
        a = tone(1318, 0.12) * env(int(0.12 * SR), r=0.08)
        b = tone(1760, 0.35) * env(int(0.35 * SR), r=0.15)
        save_wav(p, np.concatenate([a, b]) * 0.5)
    p = ROOT / "assets/se/glass.wav"        # ガラスが割れる音
    if need(p):
        n = int(1.2 * SR); t = np.arange(n) / SR; x = np.zeros(n)
        for k in range(40):
            s0 = int(rng.uniform(0, 0.5) * SR); m = int(0.25 * SR)
            f0 = rng.uniform(2500, 7000); tt = np.arange(min(m, n - s0)) / SR
            x[s0:s0 + len(tt)] += np.sin(2 * np.pi * f0 * tt) * np.exp(-tt / 0.04) * rng.uniform(0.2, 0.6)
        hp = rng.normal(0, 1, n); hp = hp - np.convolve(hp, np.ones(8) / 8, "same")
        x += hp * np.exp(-t / 0.08) * 0.8
        save_wav(p, x / np.abs(x).max() * 0.8)
    p = ROOT / "assets/se/doorbell.wav"     # ピンポーン
    if need(p):
        a = (tone(659, 0.5) + 0.3 * tone(1318, 0.5)) * env(int(0.5 * SR), r=0.35)
        b = (tone(523, 1.0) + 0.3 * tone(1046, 1.0)) * env(int(1.0 * SR), r=0.5)
        save_wav(p, np.concatenate([a[:int(0.4 * SR)], b]) * 0.45)
    p = ROOT / "assets/se/door.wav"         # ドアが開く音（ガチャ）
    if need(p):
        n = int(0.5 * SR); t = np.arange(n) / SR
        x = rng.normal(0, 1, n) * (np.exp(-t / 0.01) + 0.6 * np.exp(-np.maximum(t - 0.12, 0) / 0.015) * (t > 0.12))
        x += np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.05) * 0.5
        save_wav(p, x / np.abs(x).max() * 0.6)
    p = ROOT / "assets/bgm/bgm.wav"         # のんきなループBGM
    if need(p):
        bpm = 112; beat = 60 / bpm
        mel = [67, 69, 72, 69, 67, 64, 62, 64, 67, 69, 72, 74, 72, 69, 67, -1,
               64, 67, 69, 67, 64, 62, 60, 62, 64, 67, 69, 72, 69, 67, 64, -1]
        bass = [48, 55, 45, 52, 41, 48, 43, 50]
        total = int(len(mel) * beat / 2 * SR)
        x = np.zeros(total)
        for i, m in enumerate(mel):
            if m < 0: continue
            s = int(i * beat / 2 * SR); n = int(beat / 2 * SR * 0.95)
            x[s:s + n] += tone(440 * 2 ** ((m - 69) / 12), n / SR, "tri") * env(n, r=0.15) * 0.35
        for i, m in enumerate(bass):
            for k in range(2):
                s = int((i * 2 + k) * beat * SR); n = int(beat * SR * 0.9)
                x[s:s + n] += tone(440 * 2 ** ((m - 69) / 12), n / SR) * env(n, r=0.25) * 0.4
        save_wav(p, x * 0.8)


if __name__ == "__main__":
    cast = json.loads((ROOT / "script/cast.json").read_text())
    for name, c in cast["characters"].items():
        make_character(name, c["color"])
    make_background()
    make_sounds()
    print("仮素材OK")
