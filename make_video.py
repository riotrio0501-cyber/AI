#!/usr/bin/env python3
"""「〇〇県民しか知らないこと3選」ショート動画ジェネレーター.

使い方:
    python make_video.py prefectures/yamagata.yaml     # 1本
    python make_video.py --all                          # prefectures/*.yaml を全部
    python make_video.py prefectures/yamagata.yaml --check   # 台本チェックと尺だけ（動画は作らない）
    python make_video.py prefectures/yamagata.yaml --strict  # 「要確認」が残っていたら中止

台本の書式は prefectures/yamagata.yaml を参照。
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pyopenjtalk
import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
FONT_PATH = ROOT / "assets/fonts/MPLUSRounded1c-ExtraBold.ttf"
TOPO_PATH = ROOT / "assets/geo/japan.topojson"
SR = 48000


# ---------------------------------------------------------------- 設定・台本

def load_yaml(p: Path) -> dict:
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class Segment:
    kind: str                 # hook / fact / outro
    narration: str
    captions: list[str]
    index: int = 0            # fact の番号 (1..3)
    speed: float = 1.2
    audio: np.ndarray | None = None
    start: float = 0.0
    dur: float = 0.0
    cap_times: list[float] = field(default_factory=list)
    photo: object = None      # 写真パス / {"file":..., "focus":[x,y]} / {"emoji": "🍜"} / それらのリスト


def build_segments(script: dict, series: dict) -> list[Segment]:
    v = voice_config(script, series)
    speed = v.get("speed", 1.0)
    segs = [Segment("hook", script["hook"].get("reading") or script["hook"]["narration"],
                    script["hook"]["captions"], speed=v.get("hook_speed", speed))]
    for i, f in enumerate(script["facts"], 1):
        segs.append(Segment("fact", f.get("reading") or f["narration"], f["captions"], i, speed,
                            photo=f.get("photo")))
    segs.append(Segment("outro", script["outro"].get("reading") or script["outro"]["narration"],
                        script["outro"]["captions"], speed=speed))
    return segs


def validate(script: dict, path: Path) -> list[str]:
    warns = []
    if len(script.get("facts", [])) != 3:
        warns.append(f"ネタが{len(script.get('facts', []))}個です（3個の想定）")
    for i, f in enumerate(script.get("facts", []), 1):
        # ok = 根拠あり / 説 = 諸説ありとして「〜という説」等の言い方で紹介（根拠メモは必須）
        if f.get("status", "要確認") not in ("ok", "説"):
            warns.append(f"ネタ{i}「{f.get('title', '')}」が status: {f.get('status', '未記入')}")
        if not f.get("evidence"):
            warns.append(f"ネタ{i}「{f.get('title', '')}」に根拠(evidence)がありません")
    for part in [script["hook"], *script["facts"], script["outro"]]:
        for c in part["captions"]:
            n = len(re.sub(r"[\[\]{}/]", "", c))
            if n > 15:
                warns.append(f"テロップが{n}文字: {c}（15文字以内推奨）")
    return warns


# ---------------------------------------------------------------- 音声

def voice_config(script: dict, series: dict) -> dict:
    v = dict(series.get("voice", {}))
    v.update(script.get("voice", {}))  # 県ファイルで上書き可
    return v


def voice_credit(v: dict) -> str | None:
    if v.get("engine", "openjtalk") == "sbv2":
        import tts_sbv2
        return tts_sbv2.credit(v.get("model", "koharune-ami"))
    return None


def tts(text: str, speed: float, v: dict) -> np.ndarray:
    if v.get("engine", "openjtalk") == "sbv2":
        import tts_sbv2
        x, sr = tts_sbv2.tts(text, model=v.get("model", "koharune-ami"), style=v.get("style", "Neutral"),
                             style_weight=v.get("style_weight", 1.0), speed=speed,
                             sdp_ratio=v.get("sdp_ratio", 0.25))
    else:
        x, sr = pyopenjtalk.tts(text, speed=speed)
        x = x.astype(np.float32) / 32768.0
    if sr != SR:
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    # 前後の無音を詰める
    idx = np.where(np.abs(x) > 0.01)[0]
    if len(idx):
        x = x[max(0, idx[0] - int(0.03 * SR)): idx[-1] + int(0.08 * SR)]
    return x / (np.abs(x).max() + 1e-9) * 0.85


def synth_bgm(total: float, seed: int) -> np.ndarray:
    """控えめなローファイ風パッド＋アルペジオ（自作・著作権フリー）。"""
    rng = np.random.default_rng(seed)
    n = int(total * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    bpm = 84
    bar = 4 * 60 / bpm
    # I - vi - IV - V 系（C, Am, F, G）を県ごとに移調して少し変化をつける
    base = 48 + int(rng.integers(0, 5))  # MIDI ノート
    prog = [[0, 4, 7, 11], [-3, 0, 4, 7], [-7, -3, 0, 4], [-5, -1, 2, 7]]

    def hz(m):
        return 440.0 * 2 ** ((m - 69) / 12)

    nbars = int(math.ceil(total / bar)) + 1
    for b in range(nbars):
        chord = prog[b % 4]
        s0 = int(b * bar * SR)
        L = int(bar * SR * 1.15)
        if s0 >= n:
            break
        L = min(L, n - s0)
        tt = np.arange(L) / SR
        env = np.minimum(1, tt / 0.6) * np.minimum(1, (bar * 1.15 - tt) / 0.6).clip(0, 1)
        pad = np.zeros(L, np.float32)
        for k, iv in enumerate(chord):
            f = hz(base + 12 + iv)
            for det in (-0.12, 0.12):
                pad += np.sin(2 * np.pi * f * (1 + det / 100) * tt + k) * 0.5
        pad += np.sin(2 * np.pi * hz(base + chord[0] - 12 + 12) * tt) * 0.9  # ベース
        out[s0:s0 + L] += (pad * env * 0.09).astype(np.float32)
        # 8分音符のやわらかいアルペジオ
        step = bar / 8
        for j in range(8):
            if rng.random() < 0.25:
                continue
            m = base + 24 + chord[[0, 1, 2, 3, 2, 1, 2, 3][j]]
            a0 = s0 + int(j * step * SR)
            AL = min(int(0.9 * SR), n - a0)
            if AL <= 0:
                continue
            ta = np.arange(AL) / SR
            pl = np.sin(2 * np.pi * hz(m) * ta) * np.exp(-ta * 5.5) * np.minimum(1, ta / 0.005)
            out[a0:a0 + AL] += (pl * 0.05).astype(np.float32)
    # ワンポールのローパスで角を取る
    a = math.exp(-2 * math.pi * 2500 / SR)
    y = np.empty_like(out)
    acc = 0.0
    # ベクトル化しづらいので scipy なしで lfilter 相当
    for i0 in range(0, n, SR):
        seg = out[i0:i0 + SR]
        ys = np.empty_like(seg)
        for i, v in enumerate(seg):
            acc = (1 - a) * v + a * acc
            ys[i] = acc
        y[i0:i0 + SR] = ys
    y /= np.abs(y).max() + 1e-9
    fade = np.minimum(1, t / 1.0) * np.minimum(1, (total - t) / 1.5).clip(0, 1)
    return (y * fade).astype(np.float32)


def build_audio(segs: list[Segment], series: dict, seed: int, v: dict) -> tuple[np.ndarray, float]:
    gap = series["gap_sec"]
    t = 0.15  # 冒頭のごく短い間
    for s in segs:
        s.audio = tts(s.narration, s.speed, v)
        s.start = t
        s.dur = len(s.audio) / SR + gap
        t += s.dur
    total = t + 0.6
    voice = np.zeros(int(total * SR), np.float32)
    for s in segs:
        i0 = int(s.start * SR)
        voice[i0:i0 + len(s.audio)] += s.audio
    bgm = synth_bgm(total, seed)
    # ダッキング：ナレーション中はBGMを下げる
    envv = np.abs(voice)
    k = int(0.25 * SR)
    envv = np.convolve(envv, np.ones(k) / k, mode="same")
    duck = 1 - 0.55 * np.clip(envv / 0.05, 0, 1)
    mix = voice + bgm * series["bgm_volume"] * duck
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    return mix, total


def write_wav(path: Path, x: np.ndarray):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- 地図シルエット

def prefecture_rings(code: int) -> list[list[tuple[float, float]]]:
    topo = json.loads(TOPO_PATH.read_text(encoding="utf-8"))
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(idx_list):
        pts = []
        for i in idx_list:
            a = arcs[i] if i >= 0 else arcs[~i][::-1]
            pts.extend(a if not pts else a[1:])
        return pts

    geom = next(g for g in topo["objects"]["japan"]["geometries"] if g["properties"]["id"] == code)
    polys = geom["arcs"] if geom["type"] == "MultiPolygon" else [geom["arcs"]]
    return [ring(p[0]) for p in polys]  # 外周のみ（穴は無視）


def silhouette_layer(code: int, color: str, box: tuple[int, int]) -> Image.Image:
    rings = prefecture_rings(code)
    allp = np.array([p for r in rings for p in r])
    lat0 = allp[:, 1].mean()
    k = math.cos(math.radians(lat0))
    xs, ys = allp[:, 0] * k, allp[:, 1]
    w, h = xs.max() - xs.min(), ys.max() - ys.min()
    S = 2  # 2倍で描いて縮小（アンチエイリアス）
    bw, bh = box[0] * S, box[1] * S
    sc = min(bw / w, bh / h)
    ox = (bw - w * sc) / 2
    oy = (bh - h * sc) / 2
    pad = 60 * S
    mask = Image.new("L", (bw + 2 * pad, bh + 2 * pad), 0)
    d = ImageDraw.Draw(mask)
    for r in rings:
        pts = [(pad + ox + (x * k - xs.min()) * sc, pad + oy + (ys.max() - y) * sc) for x, y in r]
        if len(pts) >= 3:
            d.polygon(pts, fill=255)
    mask = mask.resize((mask.width // S, mask.height // S), Image.LANCZOS)
    rgb = hex_rgb(color)
    glow = mask.filter(ImageFilter.GaussianBlur(28))
    layer = Image.new("RGBA", mask.size, rgb + (0,))
    a = np.maximum(np.asarray(mask, np.float32) * 0.2, np.asarray(glow, np.float32) * 0.32)
    layer.putalpha(Image.fromarray(a.clip(0, 255).astype(np.uint8)))
    # 輪郭線
    edge = mask.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.MaxFilter(3))
    line = Image.new("RGBA", mask.size, lighten(rgb, 0.45) + (0,))
    line.putalpha(Image.fromarray((np.asarray(edge, np.float32) * 0.6).astype(np.uint8)))
    return Image.alpha_composite(layer, line)


# ---------------------------------------------------------------- 描画ユーティリティ

def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lighten(c, a):
    return tuple(int(v + (255 - v) * a) for v in c)


def mix(c1, c2, a):
    return tuple(int(c1[i] * (1 - a) + c2[i] * a) for i in range(3))


_fonts: dict[int, ImageFont.FreeTypeFont] = {}


def font(size: int) -> ImageFont.FreeTypeFont:
    if size not in _fonts:
        _fonts[size] = ImageFont.truetype(str(FONT_PATH), size)
    return _fonts[size]


def parse_markup(s: str) -> list[tuple[str, int]]:
    """[..] → 1(県カラー), {..} → 2(強調黄), それ以外 0。"""
    out, style = [], 0
    for ch in s:
        if ch == "[":
            style = 1
        elif ch == "{":
            style = 2
        elif ch in "]}":
            style = 0
        else:
            out.append((ch, style))
    return out


BREAK_AFTER = set("はがをにでともの、」）×・")


def wrap(chars, fnt, max_w) -> list[list[tuple[str, int]]]:
    # "/" で明示的に改行
    if any(c == "/" for c, _ in chars):
        lines, cur = [], []
        for c in chars:
            if c[0] == "/":
                lines.append(cur)
                cur = []
            else:
                cur.append(c)
        return lines + [cur]
    text = "".join(c for c, _ in chars)
    if fnt.getlength(text) <= max_w:
        return [chars]
    n = len(chars)
    best, best_score = None, 1e9
    for i in range(2, n - 1):
        # 強調ブロックの途中では折り返さない
        if chars[i - 1][1] != 0 and chars[i][1] == chars[i - 1][1]:
            continue
        # 良い切れ目（助詞・記号の後、色の変わり目）だけを候補にする
        if not (chars[i - 1][0] in BREAK_AFTER or chars[i][1] != chars[i - 1][1]):
            continue
        l = fnt.getlength(text[:i])
        r = fnt.getlength(text[i:])
        score = abs(l - r) + (1000 if max(l, r) > max_w else 0)
        if score < best_score:
            best, best_score = i, score
    if best is None:
        # 良い切れ目がない（単語の途中になる）ときは改行せず、文字を小さくして1行に収める
        return [chars]
    return [chars[:best], chars[best:]]


def render_caption(text: str, colors: dict, max_w=960, size=118) -> Image.Image:
    chars = parse_markup(text)
    while True:
        fnt = font(size)
        lines = wrap(chars, fnt, max_w)
        if all(fnt.getlength("".join(c for c, _ in ln)) <= max_w for ln in lines) or size < 60:
            break
        size -= 6
    stroke = max(10, size // 8)
    lh = int(size * 1.28)
    W = max_w + 2 * stroke + 40
    H = lh * len(lines) + 2 * stroke + 40
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ds = ImageDraw.Draw(shadow)
    for li, ln in enumerate(lines):
        lw = fnt.getlength("".join(c for c, _ in ln))
        x = (W - lw) / 2
        y = 20 + stroke + li * lh
        for ch, st in ln:
            fill = colors[st]
            ds.text((x + 6, y + 10), ch, font=fnt, fill=(0, 0, 0, 150),
                    stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
            d.text((x, y), ch, font=fnt, fill=fill, stroke_width=stroke,
                   stroke_fill=colors["stroke"])
            x += fnt.getlength(ch)
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    return Image.alpha_composite(shadow, img)


def pill(text: str, size: int, bg, fg=(255, 255, 255), padx=36, pady=18) -> Image.Image:
    fnt = font(size)
    l, t, r, b = fnt.getbbox(text)
    w, h = int(r - l + 2 * padx), int(size * 1.0 + 2 * pady)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=bg)
    d.text((w / 2, h / 2), text, font=fnt, fill=fg, anchor="mm")
    return img


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


# ---------------------------------------------------------------- 映像

def credits_for(script: dict, series: dict) -> list[str]:
    out = [series["credit"]]
    vc = voice_credit(voice_config(script, series))
    if vc:
        out.append(vc)
    return out


def photo_credits(script: dict) -> list[str]:
    out = []
    for f in script["facts"]:
        for it in photo_items(f.get("photo")):
            c = photo_credit(it)
            if c and "file" in it:
                meta = (ROOT / it["file"]).with_suffix(".json")
                page = json.loads(meta.read_text(encoding="utf-8")).get("page") if meta.exists() else None
                c = f"{c} {page}" if page else c
            if c and c not in out:
                out.append(c)
    return out


# ---------------------------------------------------------------- 写真カード

CARD_W, CARD_H, CARD_TOP = 900, 620, 400
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def photo_items(p) -> list[dict]:
    if p is None:
        return []
    items = p if isinstance(p, list) else [p]
    return [{"file": x} if isinstance(x, str) else dict(x) for x in items]


def photo_credit(item: dict) -> str | None:
    if "credit" in item:
        return item["credit"]
    if "file" in item:
        meta = (ROOT / item["file"]).with_suffix(".json")
        if meta.exists():
            return json.loads(meta.read_text(encoding="utf-8")).get("credit")
    return None


def cover(img: Image.Image, w: int, h: int, focus=(0.5, 0.5)) -> Image.Image:
    """w×h を覆うように拡大して focus を中心に切り抜く。"""
    sc = max(w / img.width, h / img.height)
    im = img.resize((max(w, round(img.width * sc)), max(h, round(img.height * sc))), Image.LANCZOS)
    x = min(max(0, int(im.width * focus[0] - w / 2)), im.width - w)
    y = min(max(0, int(im.height * focus[1] - h / 2)), im.height - h)
    return im.crop((x, y, x + w, y + h))


def emoji_image(ch: str, size: int, bg) -> Image.Image:
    f = ImageFont.truetype(EMOJI_FONT, 109)
    tmp = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(tmp).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
    tmp = tmp.crop(tmp.getbbox() or (0, 0, 160, 160))
    s = size / max(tmp.size)
    tmp = tmp.resize((int(tmp.width * s), int(tmp.height * s)), Image.LANCZOS)
    img = Image.new("RGBA", (CARD_W, CARD_H), bg + (255,))
    img.alpha_composite(tmp, ((CARD_W - tmp.width) // 2, (CARD_H - tmp.height) // 2))
    return img


def card_mask(w, h, r=40) -> Image.Image:
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    return m


class Renderer:
    def __init__(self, script: dict, series: dict, segs: list[Segment], total: float):
        self.W, self.H = series["size"]
        self.fps = series["fps"]
        self.segs = segs
        self.total = total
        main = hex_rgb(script["color"]["main"])
        dark = hex_rgb(script["color"].get("dark", "#101018"))
        self.main = main
        self.colors = {0: (255, 255, 255), 1: lighten(main, 0.3), 2: hex_rgb(series["highlight_color"]),
                       "stroke": mix(dark, (0, 0, 0), 0.55)}
        # 背景グラデーション
        top, bottom = mix(dark, main, 0.42), mix(dark, (0, 0, 0), 0.35)
        g = np.linspace(0, 1, self.H)[:, None, None]
        grad = (np.array(top) * (1 - g) + np.array(bottom) * g) * np.ones((1, self.W, 1))
        # ほんのりビネット
        yy, xx = np.mgrid[0:self.H, 0:self.W]
        v = 1 - 0.35 * (((xx - self.W / 2) / self.W) ** 2 + ((yy - self.H / 2) / self.H) ** 2) * 2.2
        self.bg = Image.fromarray((grad * v[..., None]).clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")
        self.sil = silhouette_layer(script["code"], script["color"]["main"], (1000, 1150))
        # 固定パーツ
        hdr = series["header"].format(prefecture=script["prefecture"])
        self.header = pill(hdr, 58, bg=main + (235,))
        self.credits = [pill(c, 22, bg=(0, 0, 0, 90), fg=(255, 255, 255, 200), padx=16, pady=7)
                        for c in credits_for(script, series)]
        self.badges = {i: pill(f"その{i}", 54, bg=(255, 255, 255, 240), fg=mix(dark, main, 0.3), padx=34, pady=14)
                       for i in (1, 2, 3)}
        rng = np.random.default_rng(script["code"])
        self.particles = [(rng.random() * self.W, rng.random() * self.H, 3 + rng.random() * 7,
                           0.2 + rng.random() * 0.6, rng.random() * 6.28) for _ in range(26)]
        # テロップの表示タイミング（文字数で按分）
        for s in segs:
            lens = [max(4, len(re.sub(r"[\[\]{}/]", "", c))) for c in s.captions]
            acc, s.cap_times = 0.0, []
            for L in lens:
                s.cap_times.append(s.start + s.dur * acc / sum(lens))
                acc += L
            if s.kind == "hook":
                s.cap_times[0] = 0.0  # フックは0秒目から
        self.cap_cache: dict[str, Image.Image] = {}
        # 写真カードの準備（Ken Burns 用に少し大きめに用意）
        self.photos = {}
        zoom = 1.12
        bw, bh = int(CARD_W * zoom), int(CARD_H * zoom)
        emoji_bg = mix(dark, main, 0.25)
        for s in segs:
            out = []
            for it in photo_items(s.photo):
                if "emoji" in it:
                    base = emoji_image(it["emoji"], 420, emoji_bg).resize((bw, bh), Image.LANCZOS)
                else:
                    src = Image.open(ROOT / it["file"]).convert("RGB")
                    base = cover(src, bw, bh, tuple(it.get("focus", (0.5, 0.5)))).convert("RGBA")
                cr = photo_credit(it)
                cp = pill(cr, 20, bg=(0, 0, 0, 120), fg=(255, 255, 255, 220), padx=14, pady=6) if cr else None
                out.append((base, cp))
            if out:
                self.photos[id(s)] = out
        self.card_mask = card_mask(CARD_W, CARD_H)
        sh = Image.new("RGBA", (CARD_W + 80, CARD_H + 80), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle((40, 50, 40 + CARD_W, 50 + CARD_H), radius=40, fill=(0, 0, 0, 140))
        self.card_shadow = sh.filter(ImageFilter.GaussianBlur(18))

    def caption_img(self, text):
        if text not in self.cap_cache:
            self.cap_cache[text] = render_caption(text, self.colors)
        return self.cap_cache[text]

    def frame(self, t: float) -> Image.Image:
        im = self.bg.copy()
        W, H = self.W, self.H
        # シルエット：ゆっくり拡大＋ゆらぎ
        z = 1.0 + 0.06 * (t / self.total)
        sw, sh = int(self.sil.width * z), int(self.sil.height * z)
        sil = self.sil.resize((sw, sh), Image.BILINEAR)
        cx = W / 2 + 14 * math.sin(t * 0.5)
        cy = H * 0.53 + 18 * math.sin(t * 0.37)
        im.alpha_composite(sil, (int(cx - sw / 2), int(cy - sh / 2)))
        # 光の粒
        d = ImageDraw.Draw(im)
        for px, py, r, sp, ph in self.particles:
            y = (py - t * 40 * sp) % H
            x = px + 20 * math.sin(t * sp + ph)
            a = int(60 + 50 * math.sin(t * 1.3 + ph))
            d.ellipse((x - r, y - r, x + r, y + r), fill=lighten(self.main, 0.6) + (a,))
        # ヘッダー
        im.alpha_composite(self.header, ((W - self.header.width) // 2, 250))
        # 現在のシーン
        seg = next((s for s in reversed(self.segs) if t >= s.start), self.segs[0])
        photos = self.photos.get(id(seg))
        cap_y = H * 0.47
        badge_y = 640
        if photos:
            cap_y = CARD_TOP + CARD_H + 175
            badge_y = CARD_TOP
            self.draw_photo(im, seg, photos, t)
        if seg.kind == "fact":
            b = self.badges[seg.index]
            k = min(1, (t - seg.start) / 0.25)
            s = 0.6 + 0.4 * ease_out_back(k)
            bb = b.resize((max(1, int(b.width * s)), max(1, int(b.height * s))), Image.BILINEAR)
            im.alpha_composite(bb, ((W - bb.width) // 2, badge_y - bb.height // 2))
            self.progress(d, seg.index)
        # テロップ
        ci = 0
        for i, ct in enumerate(seg.cap_times):
            if t >= ct:
                ci = i
        cap = self.caption_img(seg.captions[ci])
        k = min(1, (t - seg.cap_times[ci]) / 0.18) if seg.cap_times[ci] > 0 else 1
        s = 0.82 + 0.18 * ease_out_back(k)
        c = cap.resize((max(1, int(cap.width * s)), max(1, int(cap.height * s))), Image.BILINEAR) if s != 1 else cap
        if k < 1:
            a = np.asarray(c.getchannel("A"), np.float32) * min(1, k * 1.6)
            c.putalpha(Image.fromarray(a.astype(np.uint8)))
        im.alpha_composite(c, ((W - c.width) // 2, int(cap_y - c.height / 2)))
        for i, c in enumerate(self.credits):
            im.alpha_composite(c, ((W - c.width) // 2, 1545 + i * 46))
        return im.convert("RGB")

    def draw_photo(self, im: Image.Image, seg, photos, t: float):
        W = self.W
        n = len(photos)
        local = t - seg.start
        i = min(n - 1, int(local / (seg.dur / n)))
        base, cp = photos[i]
        p = (local - i * seg.dur / n) / (seg.dur / n)  # この写真内の進み 0→1
        # Ken Burns：ゆっくりズーム＋少しパン
        z = 1.12 - 0.10 * p
        cw, ch = int(base.width / 1.12 * z), int(base.height / 1.12 * z)
        x0 = int((base.width - cw) * (0.5 + 0.3 * (p - 0.5) * (1 if seg.index % 2 else -1)))
        y0 = (base.height - ch) // 2
        frame = base.crop((x0, y0, x0 + cw, y0 + ch)).resize((CARD_W, CARD_H), Image.BILINEAR)
        frame.putalpha(self.card_mask)
        # 登場アニメ（下からふわっと）
        k = min(1, local / 0.35)
        e = 1 - (1 - k) ** 3
        dy = int(60 * (1 - e))
        x = (W - CARD_W) // 2
        y = CARD_TOP + dy
        if k < 1:
            a = np.asarray(frame.getchannel("A"), np.float32) * e
            frame.putalpha(Image.fromarray(a.astype(np.uint8)))
        im.alpha_composite(self.card_shadow, (x - 40, y - 40))
        im.alpha_composite(frame, (x, y))
        # 白い縁取り
        ImageDraw.Draw(im).rounded_rectangle((x - 3, y - 3, x + CARD_W + 2, y + CARD_H + 2), radius=42,
                                              outline=(255, 255, 255, int(220 * e)), width=6)
        if cp:
            im.alpha_composite(cp, (x + CARD_W - cp.width - 14, y + CARD_H - cp.height - 14))

    def progress(self, d: ImageDraw.ImageDraw, idx: int):
        y, gap = 1440, 46
        for i in range(1, 4):
            x = self.W / 2 + (i - 2) * gap
            r = 11 if i == idx else 8
            fill = (255, 255, 255, 240) if i <= idx else (255, 255, 255, 90)
            d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


# ---------------------------------------------------------------- メイン

def make(path: Path, series: dict, args) -> bool:
    script = load_yaml(path)
    name = path.stem
    print(f"\n=== {script['prefecture']} ({path}) ===")
    warns = validate(script, path)
    for w in warns:
        print(f"  ⚠ {w}")
    if args.strict and any("status" in w for w in warns):
        print("  --strict のため中止（要確認が残っています）")
        return False
    segs = build_segments(script, series)
    v = voice_config(script, series)
    print(f"  声: {v.get('engine')} / {v.get('model', '-')}")
    audio, total = build_audio(segs, series, seed=script["code"], v=v)
    for s in segs:
        lab = f"その{s.index}" if s.kind == "fact" else s.kind
        print(f"  {lab:6s} {s.start:5.1f}–{s.start + s.dur:5.1f}s  ({s.dur:.1f}s)")
    lo, hi = series["duration_range"]
    print(f"  合計 {total:.1f}s" + ("" if lo <= total <= hi else f"  ⚠ {lo}〜{hi}秒の範囲外"))
    if args.check:
        return True

    out_dir = ROOT / "out"
    out_dir.mkdir(exist_ok=True)
    wav = out_dir / f"{name}.wav"
    mp4 = out_dir / f"{name}.mp4"
    write_wav(wav, audio)
    r = Renderer(script, series, segs, total)
    fps = series["fps"]
    nframes = int(total * fps)
    W, H = series["size"]
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
           "-i", str(wav),
           "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(mp4)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(nframes):
        p.stdin.write(r.frame(f / fps).tobytes())
        if f % (fps * 5) == 0:
            print(f"  render {f / fps:4.1f}s / {total:.1f}s", flush=True)
    p.stdin.close()
    p.wait()
    wav.unlink()
    post = out_dir / f"{name}_投稿文.txt"
    hdr = series["header"].format(prefecture=script["prefecture"])
    q = script.get("comment_question", "")
    post.write_text(f"{hdr}\n\n" + (f"{q}\n" if q else "") + "あなたの県のあるあるもコメントで教えて！\n\n"
                    f"#{script['prefecture']} #県民あるある #ご当地ネタ\n\n"
                    + "\n".join(credits_for(script, series) + photo_credits(script)) + "\n", encoding="utf-8")
    print(f"  ✔ {mp4.relative_to(ROOT)}")
    return p.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scripts", nargs="*", type=Path)
    ap.add_argument("--all", action="store_true", help="prefectures/*.yaml を全部作る")
    ap.add_argument("--check", action="store_true", help="台本チェックと尺の確認だけ")
    ap.add_argument("--strict", action="store_true", help="要確認が残っていたら作らない")
    args = ap.parse_args()
    series = load_yaml(ROOT / "series.yaml")
    paths = sorted((ROOT / "prefectures").glob("*.yaml")) if args.all else args.scripts
    if not paths:
        ap.print_help()
        sys.exit(1)
    ok = all([make(p, series, args) for p in paths])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
