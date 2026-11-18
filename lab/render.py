"""1本の台本 → mp4 / キャプション を書き出す"""
import math
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import audio, config, tts
from .config import FPS, GOLD, GREEN, H, NAVY, W, WHITE
from .script import GOLD_RE, Script

TEXT_MAX_W = W - 2 * config.SAFE_SIDE - 20
TELOP_CY = 880


@lru_cache(maxsize=64)
def font(size, weight="black"):
    path, idx = config.FONT_BLACK if weight == "black" else config.FONT_BOLD
    return ImageFont.truetype(path, size, index=idx)


def ease_out_back(x):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ---------- 背景 ----------
class Background:
    def __init__(self, seed=0):
        rng = np.random.default_rng(seed)
        # 縦グラデーション（中央が少し明るい紺）
        y = np.linspace(0, 1, H)[:, None]
        x = np.linspace(-1, 1, W)[None, :]
        glow = np.exp(-((y - 0.42) ** 2) / 0.08 - x ** 2 / 1.2)
        base = np.array(NAVY, np.float32)[None, None, :] * (0.78 + 0.45 * glow[..., None])
        self.base = Image.fromarray(base.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")
        # 斜めストライプ（ゆっくり流れる）
        self.period = 120
        sw, sh = W + self.period * 2, H
        st = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        d = ImageDraw.Draw(st)
        for i in range(-sh // self.period - 2, sw // self.period + 2):
            x0 = i * self.period
            d.polygon([(x0, sh), (x0 + 36, sh), (x0 + 36 + sh * 0.5, 0), (x0 + sh * 0.5, 0)], fill=(255, 255, 255, 9))
        self.stripes = st
        # ぼかした円（緑・金）
        self.blobs = []
        for i in range(5):
            r = int(rng.integers(160, 300))
            col = GREEN if i % 2 == 0 else GOLD
            im = Image.new("RGBA", (r * 3, r * 3), (0, 0, 0, 0))
            ImageDraw.Draw(im).ellipse([r, r, 2 * r, 2 * r], fill=col + (60 if col == GREEN else 38,))
            im = im.filter(ImageFilter.GaussianBlur(r * 0.45))
            self.blobs.append(dict(img=im, cx=rng.uniform(0, W), cy=rng.uniform(200, H - 200),
                                   ax=rng.uniform(60, 160), ay=rng.uniform(60, 200),
                                   sp=rng.uniform(0.08, 0.18), ph=rng.uniform(0, 6.28)))
        # 小さな「¥」「%」パーティクル
        self.parts = []
        for c in "¥%¥円¥%":
            sz = int(rng.integers(40, 80))
            sp = Image.new("RGBA", (sz * 2, sz * 2), (0, 0, 0, 0))
            ImageDraw.Draw(sp).text((sz, sz), c, font=font(sz), anchor="mm",
                                    fill=(255, 255, 255, int(rng.integers(14, 30))))
            self.parts.append(dict(img=sp, x=rng.uniform(40, W - 160), y=rng.uniform(0, H), sp=rng.uniform(18, 40)))
        # 進捗バーの下地
        self.track = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(self.track).rounded_rectangle(
            [config.SAFE_SIDE - 20, 110, W - config.SAFE_SIDE + 20, 120], radius=5, fill=(255, 255, 255, 40))

    def frame(self, t):
        im = self.base.copy()
        off = int(t * 20) % self.period
        im.alpha_composite(self.stripes.crop((off, 0, off + W, H)))
        for b in self.blobs:
            x = b["cx"] + b["ax"] * math.sin(t * b["sp"] * 6.28 + b["ph"])
            y = b["cy"] + b["ay"] * math.cos(t * b["sp"] * 5.0 + b["ph"])
            bi = b["img"]
            im.alpha_composite(bi, (int(x - bi.width / 2), int(y - bi.height / 2))) if _inside(x, y, bi) else None
        for p in self.parts:
            y = (p["y"] - t * p["sp"]) % (H + 200) - 150
            im.alpha_composite(p["img"], (int(p["x"]), int(y)))
        im.alpha_composite(self.track)
        return im


def _inside(x, y, bi):
    return -bi.width < x < W + bi.width and -bi.height < y < H + bi.height


# ---------- テロップ ----------
def parse_line(line):
    """'2年目の[[6月]]から' → [('2年目の',False),('6月',True),('から',False)]"""
    segs, pos = [], 0
    for m in GOLD_RE.finditer(line):
        if m.start() > pos:
            segs.append((line[pos:m.start()], False))
        segs.append((m.group(1), True))
        pos = m.end()
    if pos < len(line):
        segs.append((line[pos:], False))
    return segs


GOLD_SCALE = 1.14


def line_width(segs, size):
    return sum(font(int(size * (GOLD_SCALE if g else 1))).getlength(s) for s, g in segs)


def render_telop(text, max_size=118, min_size=60):
    lines = [parse_line(l) for l in text.split("\n")]
    size = max_size
    while size > min_size and max(line_width(l, size) for l in lines) > TEXT_MAX_W:
        size -= 2
    stroke = max(6, size // 12)
    lh = int(size * GOLD_SCALE * 1.28)
    pad = stroke * 2 + 30
    wmax = int(max(line_width(l, size) for l in lines)) + pad * 2
    hh = lh * len(lines) + pad * 2
    im = Image.new("RGBA", (wmax, hh), (0, 0, 0, 0))
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d, ds = ImageDraw.Draw(im), ImageDraw.Draw(shadow)
    for i, segs in enumerate(lines):
        x = (wmax - line_width(segs, size)) / 2
        base_y = pad + i * lh + lh * 0.82  # ベースライン
        for s, g in segs:
            f = font(int(size * (GOLD_SCALE if g else 1)))
            kw = dict(font=f, anchor="ls", stroke_width=stroke)
            ds.text((x + 6, base_y + 10), s, fill=(0, 0, 0, 150), stroke_fill=(0, 0, 0, 150), **kw)
            d.text((x, base_y), s, fill=GOLD if g else WHITE, stroke_fill=NAVY, **kw)
            x += f.getlength(s)
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    shadow.alpha_composite(im)
    return shadow


def pill(text, bg, fg=WHITE, size=46):
    f = font(size)
    tw = f.getlength(text)
    im = Image.new("RGBA", (int(tw + size * 1.4), int(size * 1.7)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], radius=im.height // 2, fill=bg)
    d.text((im.width / 2, im.height / 2), text, font=f, fill=fg, anchor="mm")
    return im


def role_label(sc, script):
    if sc.role == "point":
        return pill(f"POINT {sc.number}" if sc.number else "POINT", GREEN + (255,))
    if sc.role == "who":
        return pill("こんな人向け", GREEN + (255,))
    if sc.role == "caution":
        return pill("注意", GOLD + (255,), fg=NAVY)
    if sc.role == "hook":
        return pill("知らなきゃ損", (255, 255, 255, 235), fg=NAVY, size=40)
    return None


def bookmark_icon(size=150):
    im = Image.new("RGBA", (size, int(size * 1.25)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    w, h = im.size
    d.rounded_rectangle([0, 0, w - 1, h * 0.75], radius=18, fill=GOLD)
    d.polygon([(0, h * 0.6), (w - 1, h * 0.6), (w - 1, h - 1), (w / 2, h * 0.72), (0, h - 1)], fill=GOLD)
    return im


def brand_layer(script):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x, y = config.SAFE_SIDE - 20, config.SAFE_TOP + 10
    d.ellipse([x, y + 10, x + 22, y + 32], fill=GREEN)
    d.text((x + 34, y), config.ACCOUNT_NAME, font=font(34), fill=(255, 255, 255, 230))
    d.text((x + 34, y + 44), config.ACCOUNT_ID, font=font(26, "bold"), fill=(255, 255, 255, 150))
    # 出典・年度
    orgs = []
    for s in script.sources:
        org = re.split(r"[「 　]", s.get("label", "") if isinstance(s, dict) else "")[0]
        if org and org not in orgs:
            orgs.append(org)
    info = f"※{script.info_year}の情報　出典：{'・'.join(orgs[:2])}" + ("ほか" if len(orgs) > 2 else "")
    lines = [info] + ([script.age_note] if script.age_note else [])
    for i, text in enumerate(lines):
        size = 26
        while size > 16 and font(size, "bold").getlength(text) > W - 2 * config.SAFE_SIDE:
            size -= 1
        d.text((W / 2, config.SAFE_BOTTOM - 40 + i * 38), text, font=font(size, "bold"),
               fill=(255, 255, 255, 140), anchor="mm")
    return im


# ---------- タイムライン ----------
def build_timeline(script: Script, workdir: Path):
    voice_segs, scenes = [], []
    t = 0.15
    for sc in script.scenes:
        speed = config.TTS_SPEED * (1.06 if sc.role == "hook" else 1.0)
        x = tts.synth(sc.reading or sc.narration, speed)
        dur = len(x) / tts.SR
        scenes.append(dict(scene=sc, start=t, end=t + dur + config.SCENE_GAP))
        voice_segs.append((t, x))
        t += dur + config.SCENE_GAP
    total = t + config.TAIL
    scenes[-1]["end"] = total
    scenes[0]["start"] = 0.0
    n = int(total * tts.SR) + tts.SR
    voice = np.zeros(n, np.float32)
    for st, x in voice_segs:
        s = int(st * tts.SR)
        voice[s:s + len(x)] += x
    sfx = np.zeros(n, np.float32)
    p = audio.pop()
    for i, s in enumerate(scenes):
        k = int(max(0, s["start"] - 0.02) * tts.SR)
        snd = audio.whoosh() if i == 0 else p
        sfx[k:k + len(snd)] += snd[: n - k]
    music = audio.bgm(n / tts.SR, seed=int(script.id) if script.id.isdigit() else 0)
    # 声がある間はBGMを下げる（簡易ダッキング）
    env = np.convolve((np.abs(voice) > 0.02).astype(np.float32), np.ones(4800) / 4800, mode="same")
    music *= audio.db(config.BGM_GAIN_DB) * (1 - 0.45 * np.clip(env * 3, 0, 1))
    mix = voice + music + sfx * audio.db(config.SFX_GAIN_DB)
    mix = mix[: int(total * tts.SR)]
    mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
    wav = workdir / "audio.wav"
    audio.write_wav(wav, mix)
    return scenes, total, wav


# ---------- 書き出し ----------
def render(script: Script, outdir: Path, preview_only=False):
    outdir.mkdir(parents=True, exist_ok=True)
    scenes, total, wav = build_timeline(script, outdir)
    bg = Background(seed=int(script.id) if script.id.isdigit() else 0)
    brand = brand_layer(script)
    telops = [render_telop(s["scene"].telop, max_size=128 if s["scene"].role == "hook" else 112) for s in scenes]
    labels = [role_label(s["scene"], script) for s in scenes]
    icon = bookmark_icon()
    follow = render_telop("フォローで[[毎日お得情報]]", max_size=64) if script.length == "long" else None

    nframes = int(total * FPS)
    mp4 = outdir / f"{script.slug}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(mp4)]
    proc = None if preview_only else subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cover_t = min(scenes[0]["end"] - 0.1, 1.2)
    previews = {round(s["start"] + 0.5, 2): i for i, s in enumerate(scenes)}
    frames_out = range(nframes) if not preview_only else [int(k * FPS) for k in previews] + [int(cover_t * FPS)]

    for fi in frames_out:
        t = fi / FPS
        im = bg.frame(t)
        si = next(i for i, s in enumerate(scenes) if t < s["end"] or i == len(scenes) - 1)
        s = scenes[si]
        sc = s["scene"]
        lt = t - s["start"]
        k = min(1.0, lt / 0.22)
        scale = 0.82 + 0.18 * ease_out_back(k)
        alpha = min(1.0, lt / 0.1)
        tel = telops[si]
        cy = TELOP_CY + (60 if sc.role == "outro" else 0)
        if scale != 1.0:
            tel = tel.resize((max(1, int(tel.width * scale)), max(1, int(tel.height * scale))), Image.BILINEAR)
        if alpha < 1:
            tel = tel.copy()
            tel.putalpha(tel.getchannel("A").point(lambda a: int(a * alpha)))
        im.alpha_composite(tel, (int(W / 2 - tel.width / 2), int(cy - tel.height / 2)))
        top_of_text = cy - telops[si].height / 2
        lb = labels[si]
        if lb is not None:
            ly = int(top_of_text - lb.height + 10 - 30 * (1 - min(1, lt / 0.2)))
            im.alpha_composite(lb, (int(W / 2 - lb.width / 2), ly))
        if sc.role == "outro":
            bounce = abs(math.sin(lt * 5)) * 30 * math.exp(-lt * 1.2)
            im.alpha_composite(icon, (int(W / 2 - icon.width / 2), int(top_of_text - icon.height - 10 - bounce)))
            if follow is not None:
                im.alpha_composite(follow, (int(W / 2 - follow.width / 2), int(cy + telops[si].height / 2)))
        im.alpha_composite(brand)
        # 進捗バー
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([config.SAFE_SIDE - 20, 110, config.SAFE_SIDE - 20 + (W - 2 * config.SAFE_SIDE + 40)
                             * min(1, t / total), 120], radius=5, fill=GREEN)
        rgb = im.convert("RGB")
        if preview_only:
            if fi == int(cover_t * FPS):
                rgb.save(outdir / "cover.png")
            else:
                rgb.save(outdir / f"preview_{fi:04d}.png")
        else:
            proc.stdin.write(rgb.tobytes())
            if fi == int(cover_t * FPS):
                rgb.save(outdir / "cover.png")
    if proc:
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg failed")
    write_caption(script, outdir, total)
    return mp4, total


def write_caption(script: Script, outdir: Path, total):
    eng = tts.get_engine()
    tags = " ".join("#" + h.lstrip("#") for h in script.hashtags)
    lines = [script.caption, "", tags, ""]
    if eng.credit:
        lines.append(eng.credit)
    lines += ["", "---- 投稿前チェック用（キャプションには貼らない）----",
              f"タイトル: {script.title}", f"長さ: {script.length}（{total:.1f}秒）",
              f"対象: {' / '.join(script.targets)}", f"情報の年度: {script.info_year}", "出典:"]
    lines += [f"  - {s.get('label','')}: {s.get('url','')}" for s in script.sources]
    if script.warnings:
        lines.append("警告:")
        lines += [f"  - {w}" for w in script.warnings]
    (outdir / "caption.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
