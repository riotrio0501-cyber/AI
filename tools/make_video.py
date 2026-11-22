"""台本から動画を1本作る。
使い方:  python3 tools/make_video.py [台本.json] [出力.mp4]
  省略時: script/script.json → output/video.mp4
手順: ①VOICEVOXで音声生成（変更のないセリフは再利用） ②音を合成 ③絵を合成 ④MP4に書き出し
"""
import hashlib, json, re, subprocess, sys, wave, urllib.request, urllib.parse
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS, SR = 1080, 1920, 30, 48000
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
API = "http://localhost:50021"
API_NEMO = "http://localhost:50121"   # VOICEVOX Nemo（大人の声、話者IDが10000番台）


def api_base(speaker_id):
    return API_NEMO if int(speaker_id) >= 10000 else API

GAP = 0.32          # セリフ間の基本の間（秒）
PAUSE = 1.3         # effect "pause" で追加する間（秒）
SILENT_DEFAULT = 1.5
TAIL = 2.0          # 最後の余韻


# ---------------- 音声 ----------------
def api(path, params, body=None):
    url = f"{api_base(params['speaker'])}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def tts_text(text):
    return re.sub(r"（[^）]*）|\([^)]*\)", "", text).strip()


def is_silent(text):
    return re.sub(r"[…・。、ー！？!?\.\s「」]", "", tts_text(text)) == ""


def read_wav(path):
    import soundfile as sf
    x, sr = sf.read(str(path), dtype="float32")
    if x.ndim == 2:
        x = x.mean(1)
    if sr != SR:  # 線形補間でリサンプル
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return x


def make_voices(lines, cast):
    """声を作る。キャラの "engine" が "sbv2" なら感情つきの声、なければ VOICEVOX"""
    vdir = ROOT / "voices"; vdir.mkdir(exist_ok=True)
    for i, ln in enumerate(lines):
        if is_silent(ln["text"]):
            ln["wav"] = None; continue
        c = cast["characters"][ln["speaker"]]
        text = ln.get("yomi") or tts_text(ln["text"])
        speed = ln.get("speed", c.get("speed", cast.get("speed", 1.0)))
        volume = ln.get("volume", 1.0)
        if c.get("engine") == "sbv2":
            ln["engine"] = "sbv2"; ln["credit"] = c.get("credit")
            emo = ln.get("emotion", c.get("emotion", "ふつう"))
            emo = c.get("emotion_styles", {}).get(emo, emo)  # モデルごとの感情名に置き換え
            opts = ["sbv2", c["model"], emo,
                    ln.get("strength", c.get("strength", 2.0)), speed, volume]
        else:
            emo = ln.get("emotion", c.get("emotion", "ふつう"))
            vid = ln.get("voice_id") or c.get("emotion_styles", {}).get(emo) or c["voice_id"]
            ln["voice_id"] = vid
            opts = ["vv", vid, speed, volume, ln.get("pitch", 0.0)]
        key = hashlib.md5(json.dumps([text, opts], ensure_ascii=False).encode()).hexdigest()[:8]
        out = vdir / f"{ln['speaker']}_{key}.wav"   # 同じセリフ・同じ声なら作り直さない
        ln["wav"] = out
        if out.exists():
            continue
        if opts[0] == "sbv2":
            import sbv2, soundfile as sf
            sr, x = sbv2.synth(text, opts[1], opts[2], opts[3], speed, volume)
            sf.write(out, x, sr)
        else:
            q = json.loads(api("/audio_query", {"text": text, "speaker": opts[1]}))
            q.update(speedScale=speed, volumeScale=volume, pitchScale=opts[4],
                     prePhonemeLength=0.05, postPhonemeLength=0.08, outputSamplingRate=SR)
            out.write_bytes(api("/synthesis", {"speaker": opts[1]}, json.dumps(q).encode()))
        print(f"  音声 {i + 1:02d} {ln['speaker']}「{ln['text']}」")


# ---------------- タイミング ----------------
def effects(ln):
    e = ln.get("effect", "none")
    return set([e] if isinstance(e, str) else e)


def phone_filter(x):
    """スマホのスピーカーから出たような音（低音と高音を削る）"""
    k = np.ones(6) / 6
    lo = np.convolve(x, k, "same")
    hp = lo - np.convolve(lo, np.ones(60) / 60, "same")
    return np.clip(hp * 2.2, -0.9, 0.9) * 0.8


def inner_voice(x):
    """心の声（少し響かせる）"""
    y = x.copy()
    for d, g in ((int(0.07 * SR), 0.35), (int(0.14 * SR), 0.2), (int(0.21 * SR), 0.1)):
        y[d:] += x[:-d] * g
    return y * 0.8


def build_timeline(lines, intro=1.2):
    t = intro  # 最初はタイトルと背景だけ見せる
    for ln in lines:
        fx = effects(ln)
        t += GAP + (PAUSE if "pause" in fx else 0) + ln.get("gap", 0)
        ln["start"] = t
        if ln["wav"]:
            ln["audio"] = read_wav(ln["wav"])
            if ln.get("muffle"):  # 壁ごしの声（こもった音）
                k = np.ones(14) / 14
                ln["audio"] = np.convolve(np.convolve(ln["audio"], k, "same"), k, "same") * 0.9
            if ln.get("filter") == "phone":
                ln["audio"] = phone_filter(ln["audio"])
            if ln.get("inner"):
                ln["audio"] = inner_voice(ln["audio"])
            dur = len(ln["audio"]) / SR
        else:
            ln["audio"] = None
            dur = ln.get("pause", SILENT_DEFAULT)
        ln["end"] = t + dur
        t = ln["end"]
    return t + TAIL


def mix_audio(lines, total, cast):
    n = int(total * SR) + SR
    mix = np.zeros(n, np.float32)

    def add(x, t, gain=1.0):
        s = int(t * SR); e = min(n, s + len(x))
        mix[s:e] += x[:e - s] * gain

    for ln in lines:
        if ln["audio"] is not None:
            add(ln["audio"], ln["start"])
        if ln.get("se"):
            add(read_wav(ROOT / "assets/se" / f"{ln['se']}.wav"), max(0, ln["start"] - 0.05), 0.8)
        if ln.get("se_after"):
            add(read_wav(ROOT / "assets/se" / f"{ln['se_after']}.wav"), ln["end"] + 0.3, 0.8)
    bgm_path = ROOT / cast.get("bgm", "")
    if cast.get("bgm") and bgm_path.exists():
        b = read_wav(bgm_path)
        reps = np.tile(b, n // len(b) + 1)[:n] * cast.get("bgm_volume", 0.1)
        fade = int(1.5 * SR); end = int(total * SR)
        reps[end - fade:end] *= np.linspace(1, 0, fade); reps[end:] = 0
        mix += reps
    peak = np.abs(mix).max()
    if peak > 0.98:
        mix *= 0.98 / peak
    out = ROOT / "output/_audio.wav"; out.parent.mkdir(exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix[:int(total * SR)] * 32767).astype(np.int16).tobytes())
    return out


def mouth_track(ln, nframes):
    """各フレームで口を開けるか（音量で判定）"""
    open_ = np.zeros(nframes, bool)
    if ln["audio"] is None:
        return open_
    x = ln["audio"]; hop = SR // FPS
    rms = np.array([np.sqrt(np.mean(x[i:i + hop] ** 2)) if i < len(x) else 0 for i in range(0, len(x), hop)])
    th = max(rms.max() * 0.18, 1e-4)
    s = int(round(ln["start"] * FPS))
    for k, v in enumerate(rms):
        if v > th and s + k < nframes:
            open_[s + k] = True
    # パカパカ感を出す：開きっぱなしが続いたら3フレームごとに一瞬閉じる
    run = 0
    for f in range(s, min(nframes, s + len(rms))):
        run = run + 1 if open_[f] else 0
        if run and run % 4 == 0:
            open_[f] = False
    return open_


# ---------------- 絵 ----------------
def hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def cover_params(iw, ih, top=False):
    """画面いっぱいに拡大するときの倍率と切り抜き位置（top=True なら上をそろえて頭が切れないように）"""
    s = max(W / iw, H / ih)
    x = (round(iw * s) - W) // 2
    y = 0 if top else (round(ih * s) - H) // 2
    return s, x, y


def cover(im, top=False):
    s, x, y = cover_params(im.width, im.height, top)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    return im.crop((x, y, x + W, y + H))


def load_img(path, top=False):
    return cover(Image.open(path).convert("RGB"), top) if path.exists() else None


def face_points():
    """画像ごとの顔の位置（assets/image_plan.json の "face"）"""
    try:
        plan = json.loads((ROOT / "assets/image_plan.json").read_text())
        return {it["name"]: it["face"] for it in plan["images"] if "face" in it}
    except Exception:
        return {}


class Shots:
    """カット（場面）ごとの絵を読み込んでおく"""
    def __init__(self, cast):
        self.cast = cast; self.cache = {}; self.faces = face_points(); self.focus = {}

    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        kind, name, mouth = key
        top = W > H  # 横長では顔アップの頭が切れないよう上をそろえる
        pname = None
        if kind == "char":
            name, _, var = name.partition("|")   # var = 表情違い（例: 喜び）
            d = ROOT / "assets/characters" / name
            pre = f"{var}_" if var and (d / f"{var}_close.png").exists() else ""
            im = load_img(d / f"{pre}{mouth}.png", top) or load_img(d / f"{pre}close.png", top)
            pname, ppath = f"{name}/{pre}close", d / f"{pre}close.png"
        elif kind == "duo":
            im = self.duo(name, mouth)
        elif kind == "phone":
            im = phone_screen(json.loads(name), self.get(("bg", None, None)))
        elif kind == "shot":
            ppath = ROOT / "assets/shots" / f"{name}.png"
            im = load_img(ppath, top)
            pname = f"shots/{name}"
        else:
            im = load_img(ROOT / self.cast["background"])
        self.cache[key] = im or Image.new("RGB", (W, H), (60, 60, 60))
        if pname in self.faces:  # ズームで寄る位置
            fx, fy = self.faces[pname]
            sc, ox, oy = cover_params(*Image.open(ppath).size, top)
            self.focus[key] = (fx * sc - ox, fy * sc - oy)
        return self.cache[key]


def _duo_half(self, name, var, mouth, dim):
    """左右2分割用：キャラの顔を中心に半分の幅で切り出す"""
    from PIL import ImageEnhance
    full = self.get(("char", f"{name}|{var}", mouth))
    fx, _ = self.focus.get(("char", f"{name}|{var}", mouth), (W / 2, 0))
    x0 = int(min(max(fx - W / 4, 0), W - W / 2))
    half = full.crop((x0, 0, x0 + W // 2, H))
    return ImageEnhance.Brightness(half).enhance(0.6) if dim else half


def _duo(self, spec, mouth):
    left, right, speaker, var = spec.split("|")
    im = Image.new("RGB", (W, H))
    im.paste(self._duo_half(left, var if speaker == left else "", mouth if speaker == left else "close", speaker != left), (0, 0))
    im.paste(self._duo_half(right, var if speaker == right else "", mouth if speaker == right else "close", speaker != right), (W // 2, 0))
    ImageDraw.Draw(im).rectangle([W // 2 - 4, 0, W // 2 + 4, H], fill=(20, 20, 20))
    return im


Shots._duo_half = _duo_half
Shots.duo = _duo


def shot_key(ln, mouth_open, cast=None):
    if ln is None:
        return ("bg", None, None)
    if ln.get("phone"):
        return ("phone", json.dumps(ln["phone"], ensure_ascii=False, sort_keys=True), None)
    if ln.get("shot"):
        return ("shot", ln["shot"], None)
    mouth = "open" if mouth_open else "close"
    if ln.get("duo") and cast and cast.get("duo"):
        l, r = cast["duo"]
        return ("duo", f"{l}|{r}|{ln['speaker']}|{ln.get('emotion', '')}", mouth)
    return ("char", f"{ln['speaker']}|{ln.get('emotion', '')}", mouth)


def wrap(text, font, maxw, d):
    """行の長さがそろうように折り返す（句読点が行頭に来ないようにする）"""
    n = 1
    while True:
        per = -(-len(text) // n)
        rows, cur = [], ""
        for ch in text:
            if len(cur) >= per and ch not in "、。！？…」）ー":
                rows.append(cur); cur = ""
            cur += ch
        rows.append(cur)
        if all(d.textlength(r, font=font) <= maxw for r in rows) or n >= 4:
            return rows
        n += 1


def subtitle_layer(speaker, text, color):
    """白い文字＋話者の色のふち＋黒いふち"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    land = W > H
    f = ImageFont.truetype(FONT, 66 if land else 80)
    rows = wrap(text, f, W - (360 if land else 100), d)
    lh = 86 if land else 104
    top = (H - 50 if land else 1560) - lh * len(rows)
    for i, r in enumerate(rows):
        tw = d.textlength(r, font=f); x, y = (W - tw) / 2, top + i * lh
        d.text((x, y), r, font=f, fill="black", stroke_width=16, stroke_fill="black")
        d.text((x, y), r, font=f, fill="white", stroke_width=9, stroke_fill=hex2rgb(color))
    return layer


_SL = {}


def speed_lines():
    """集中線（画面のふちから中心に向かう線）"""
    if (W, H) not in _SL:
        rng = np.random.default_rng(3)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        cx, cy, R = W / 2, H / 2, (W ** 2 + H ** 2) ** 0.5
        for a in rng.uniform(0, 2 * np.pi, 140):
            r0 = rng.uniform(0.45, 0.6) * min(W, H); w = rng.uniform(0.004, 0.012)
            pts = [(cx + np.cos(a) * r0, cy + np.sin(a) * r0), (cx + np.cos(a - w) * R, cy + np.sin(a - w) * R),
                   (cx + np.cos(a + w) * R, cy + np.sin(a + w) * R)]
            d.polygon(pts, fill=(255, 255, 255, 150))
        _SL[(W, H)] = layer
    return _SL[(W, H)]


def title_card(title):
    """長編用：最初に出す大きなタイトル"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 120))
    d = ImageDraw.Draw(layer)
    f = ImageFont.truetype(FONT, 76)
    rows = wrap(title, f, W - 240, d)
    top = H / 2 - 50 * len(rows)
    for i, r in enumerate(rows):
        tw = d.textlength(r, font=f)
        d.text(((W - tw) / 2, top + i * 100), r, font=f, fill=(255, 236, 120), stroke_width=7, stroke_fill="black")
    return layer


def phone_screen(p, bg):
    """スマホの画面（通知・トーク・動画再生）を描く。本物のアプリのロゴやデザインは使わない"""
    from PIL import ImageFilter
    im = bg.filter(ImageFilter.GaussianBlur(18)).convert("RGBA")
    im.alpha_composite(Image.new("RGBA", im.size, (0, 0, 0, 110)))
    pw, ph = (600, 1040) if W > H else (820, 1460)
    px, py = (W - pw) // 2, (H - ph) // 2
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([px - 14, py - 14, px + pw + 14, py + ph + 14], 70, fill=(20, 20, 24))
    scr = [px, py, px + pw, py + ph]
    F = lambda n: ImageFont.truetype(FONT, n)
    sc = pw / 480
    if p["type"] == "notify":
        d.rounded_rectangle(scr, 56, fill=(32, 44, 78))
        d.text((px + pw / 2, py + 170 * sc), "23:14", font=F(int(110 * sc)), fill="white", anchor="mm")
        d.text((px + pw / 2, py + 255 * sc), "11月21日 金曜日", font=F(int(26 * sc)), fill=(220, 225, 240), anchor="mm")
        cx0, cy0, cx1 = px + 24 * sc, py + 330 * sc, px + pw - 24 * sc
        rows = []
        for para in p["text"].split("\n"):
            rows += wrap(para, F(int(27 * sc)), cx1 - cx0 - 40 * sc, d)
        cy1 = cy0 + (145 + 40 * len(rows)) * sc
        d.rounded_rectangle([cx0, cy0, cx1, cy1], 28 * sc, fill=(245, 245, 248))
        d.rounded_rectangle([cx0 + 20 * sc, cy0 + 20 * sc, cx0 + 64 * sc, cy0 + 64 * sc], 10 * sc, fill=(46, 170, 140))
        d.text((cx0 + 78 * sc, cy0 + 42 * sc), "メッセージ ・ 今", font=F(int(22 * sc)), fill=(120, 120, 130), anchor="lm")
        d.text((cx0 + 22 * sc, cy0 + 80 * sc), p["from"], font=F(int(30 * sc)), fill=(20, 20, 20))
        for i, r in enumerate(rows):
            d.text((cx0 + 22 * sc, cy0 + (122 + 40 * i) * sc), r, font=F(int(27 * sc)), fill=(40, 40, 40))
    elif p["type"] == "chat":
        d.rounded_rectangle(scr, 56, fill=(214, 224, 236))
        d.rectangle([px, py + 40 * sc, px + pw, py + 130 * sc], fill=(48, 62, 92))
        d.text((px + pw / 2, py + 85 * sc), p["title"] + " (4)", font=F(int(28 * sc)), fill="white", anchor="mm")
        y = py + 170 * sc
        for m in p["messages"]:
            f = F(int(26 * sc)); rows = wrap(m["text"], f, 330 * sc, d)
            bw = max(d.textlength(r, font=f) for r in rows) + 40 * sc; bh = (24 + 36 * len(rows)) * sc
            if m.get("mine"):
                x1 = px + pw - 24 * sc; x0 = x1 - bw
                d.rounded_rectangle([x0, y, x1, y + bh], 22 * sc, fill=(140, 220, 120))
                lab = (f"既読{m['read']}\n" if m.get("read") else "") + "23:20"
                d.multiline_text((x0 - 10 * sc, y + bh), lab, font=F(int(18 * sc)), fill=(90, 90, 100), anchor="rd", align="right")
            else:
                d.ellipse([px + 20 * sc, y, px + 72 * sc, y + 52 * sc], fill=(150, 160, 180))
                d.text((px + 86 * sc, y - 4 * sc), m["from"], font=F(int(20 * sc)), fill=(70, 70, 80))
                y += 26 * sc
                x0 = px + 86 * sc; x1 = x0 + bw
                d.rounded_rectangle([x0, y, x1, y + bh], 22 * sc, fill="white")
            for i, r in enumerate(rows):
                d.text((x0 + 20 * sc, y + (12 + 36 * i) * sc), r, font=f, fill=(20, 20, 20))
            y += bh + 36 * sc
    else:  # 動画の再生画面
        d.rounded_rectangle(scr, 56, fill=(8, 8, 10))
        cx, cy = px + pw / 2, py + ph * 0.45
        d.polygon([(cx - 40 * sc, cy - 50 * sc), (cx - 40 * sc, cy + 50 * sc), (cx + 50 * sc, cy)], fill=(230, 230, 230))
        d.rectangle([px + 40 * sc, py + ph - 140 * sc, px + pw - 40 * sc, py + ph - 132 * sc], fill=(90, 90, 90))
        d.rectangle([px + 40 * sc, py + ph - 140 * sc, px + pw * 0.45, py + ph - 132 * sc], fill=(230, 60, 60))
        d.text((px + 40 * sc, py + ph - 110 * sc), "0:18 / 0:42", font=F(int(22 * sc)), fill=(200, 200, 200))
    return im.convert("RGB")


def title_layer(title):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = ImageFont.truetype(FONT, 58)
    rows = title.split("\n")
    d.rectangle([0, 120, W, 140 + 80 * len(rows) + 30], fill=(20, 20, 30, 200))
    for i, r in enumerate(rows):
        tw = d.textlength(r, font=f)
        d.text(((W - tw) / 2, 145 + i * 80), r, font=f, fill=(255, 236, 120), stroke_width=5, stroke_fill="black")
    return layer


def render(lines, total, cast, audio, out):
    nframes = int(total * FPS)
    shots = Shots(cast)
    cur = [-1] * nframes
    for i, ln in enumerate(lines):
        s = int(ln["start"] * FPS)
        e = int(lines[i + 1]["start"] * FPS) if i + 1 < len(lines) else nframes
        for f in range(s, min(e, nframes)):
            cur[f] = i
    mouths = [mouth_track(ln, nframes) for ln in lines]
    sub_cache = {}
    intro = cast.get("title_mode") == "intro"
    title = title_card(cast["title"]) if intro else title_layer(cast["title"])
    black_from = int((lines[-1]["end"] + 0.25) * FPS) if cast.get("end") == "blackout" else nframes + 1
    rng = np.random.default_rng(1)
    z, prev_shot, shot_start = 1.0, None, 0
    last_scene, trans_until, cuts = None, -1, 0
    duo_chars = cast.get("duo") or []

    def listener_of(ln):
        """聞き手（リアクションを映す相手）"""
        if ln.get("listener"):
            return ln["listener"]
        others = [c for c in duo_chars if c != ln["speaker"]]
        return others[0] if others else None

    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(audio),
                           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
                          stdin=subprocess.PIPE)
    for f in range(nframes):
        i = cur[f]
        ln = lines[i] if i >= 0 else None
        key = shot_key(ln, bool(mouths[i][f]) if ln else False, cast)
        if ln:
            el_line = f / FPS - ln["start"]; dur = ln["end"] - ln["start"]
            # 場面の頭は「二人の引きの絵」から入る
            if ln.get("establish") and cast.get("wide") and el_line < min(1.6, 0.5 * dur):
                key = ("shot", cast["wide"], None)
            # 長いセリフの後半は、聞いている相手のリアクションに切り替える
            elif (key[0] == "char" and not ln.get("no_react") and dur >= 2.0 and el_line > 0.55 * dur
                  and listener_of(ln)):
                react = ln.get("react") or ("悲しみ" if ln.get("emotion") == "悲しみ" else "驚き")
                key = ("char", f"{listener_of(ln)}|{react}", "close")
        scene = shots.get(key)
        shot_id = key[:2]
        if shot_id != prev_shot:          # カットが変わったらカメラをリセット
            cuts += 1
            # 3回に1回くらい、横にシュッと流れる切り替えにする
            if last_scene is not None and cuts % 3 == 0 and key[0] in ("char", "shot", "duo"):
                trans_until = f + 5; trans_from = last_scene
            prev_shot, shot_start, z = shot_id, f, 1.0
        fx = effects(ln) if ln else set()
        # カメラの動き：カットごとに「寄る／引く／左右に流す」を切り替える
        el_shot = (f - shot_start) / FPS
        move = (sum(map(ord, str(shot_id))) + i) % 4 if ln else 0
        if key[0] in ("phone", "duo"):
            move = 0
        if move == 0:
            drift = 1.0 + min(0.025 * el_shot, 0.14)          # 寄る
        elif move == 1:
            drift = 1.14 - min(0.025 * el_shot, 0.12)         # 引く
        else:
            drift = 1.12                                       # 左右に流す
        tz = 1.3 if "zoom" in fx else 1.0
        z += (tz - z) * 0.3
        zz = max(1.03, min(z * drift, 1.4))   # 少し余白を持たせて動かせるようにする
        cx, cy = shots.focus.get(key, (W / 2, H * 0.36))
        if move >= 2 and "zoom" not in fx:
            cx += (1 if move == 2 else -1) * (min(el_shot, 4) / 4 - 0.5) * W * 0.1
        sx = sy = 0.0
        if ln and key[0] in ("char", "duo") and 0 <= f / FPS - ln["start"] < 0.2:   # しゃべり始めにぴょこっと動く
            sy = -14 * np.sin(np.pi * (f / FPS - ln["start"]) / 0.2)
        if "shake" in fx:
            el = f / FPS - ln["start"]
            if 0 <= el < 0.6:
                amp = 30 * (1 - el / 0.6)
                sx, sy = rng.uniform(-amp, amp, 2)
                zz = max(zz, 1.08)
        bw, bh = W / zz, H / zz
        x0 = min(max(cx - bw / 2 + sx, 0), W - bw); y0 = min(max(cy - bh / 2 + sy, 0), H - bh)
        frame = scene.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + bw, y0 + bh)) if zz > 1.001 else scene
        last_scene = frame
        if f < trans_until:   # 横に流れる切り替え（前の絵が左へ、新しい絵が右から）
            t = 1 - (trans_until - f) / 5
            blur = lambda im: im.resize((W // 16, H)).resize((W, H), Image.BILINEAR)
            canvas = Image.new("RGB", (W, H))
            canvas.paste(blur(trans_from), (int(-W * t), 0))
            canvas.paste(blur(frame) if t < 0.8 else frame, (int(W * (1 - t)), 0))
            frame = canvas
        frame = frame.convert("RGBA")
        if f >= black_from:  # 暗転
            ff.stdin.write(bytes(W * H * 3)); continue
        if not intro or ln is None:
            frame.alpha_composite(title)
        if ln and "shake" in fx and 0 <= f / FPS - ln["start"] < 0.5:   # 衝撃：集中線とフラッシュ
            el = f / FPS - ln["start"]
            frame.alpha_composite(speed_lines())
            if el < 0.1:
                frame.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(150 * (1 - el / 0.1)))))
        if ln and ln.get("phone", {}).get("type") not in ("notify", "chat"):
            if i not in sub_cache:
                sub_cache[i] = subtitle_layer(ln["speaker"], ln["text"], cast["characters"][ln["speaker"]]["color"])
            el = f / FPS - ln["start"]
            frame.alpha_composite(sub_cache[i], (0, int(max(0, 1 - el / 0.13) * 24)))
        ff.stdin.write(frame.convert("RGB").tobytes())
        if f % 150 == 0:
            print(f"  映像 {f}/{nframes} フレーム", end="\r")
    ff.stdin.close(); ff.wait()
    print()


def write_credits(lines, out):
    names, sbv = [], False
    try:
        idname = {}
        for base in (API, API_NEMO):
            try:
                sp = json.loads(urllib.request.urlopen(f"{base}/speakers", timeout=10).read())
                idname.update({st["id"]: (s["name"], s["speaker_uuid"]) for s in sp for st in s["styles"]})
            except Exception:
                pass
    except Exception:
        idname = {}
    for ln in lines:
        if ln.get("engine") == "sbv2":
            if ln.get("credit"):
                for cr in ([ln["credit"]] if isinstance(ln["credit"], str) else ln["credit"]):
                    if cr not in names:
                        names.append(cr)
            else:
                sbv = True
            continue
        n = idname.get(ln.get("voice_id"))
        if not n:
            continue
        credit = f"VOICEVOX:{n[0]}"
        try:  # キャラごとに指定されたクレジット表記があればそれを使う（例: もち子さん）
            pol = json.loads(urllib.request.urlopen(f"{api_base(ln['voice_id'])}/speaker_info?speaker_uuid={n[1]}", timeout=10).read())["policy"]
            m = re.search(r"「(VOICEVOX[^」]*)」", pol)
            if m:
                credit = m.group(1)
        except Exception:
            pass
        if credit not in names:
            names.append(credit)
    rows = list(names)
    if sbv:
        rows += ["音声合成：Style-Bert-VITS2", "音声モデル：JVNV (CC BY-SA 4.0) https://sites.google.com/site/shinnosuketakamichi/research-topics/jvnv_corpus"]
    rows += ["画像生成：Animagine XL 4.0", "効果音・BGM：自作"]
    txt = "【概要欄用クレジット】\n" + "\n".join(rows) + "\n"
    out.write_text(txt, encoding="utf-8")
    return txt


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    script = Path(args[0]) if args else ROOT / "script/script.json"
    out = Path(args[1]) if len(args) > 1 else ROOT / "output/video.mp4"
    cast = json.loads((ROOT / "script/cast.json").read_text())
    data = json.loads(Path(script).read_text())
    if isinstance(data, dict):  # {"title": ..., "lines": [...]} 形式（回ごとにタイトルを持てる）
        cast["title"] = data.get("title", cast["title"]); lines = data["lines"]
        if data.get("cast"):  # 回ごとの配役・背景・画面の向き
            cast.update(data["cast"])
    else:
        lines = data
    global W, H
    if cast.get("format") == "landscape":
        W, H = 1920, 1080
    print("① 音声を作成"); make_voices(lines, cast)
    if "--voices-only" in sys.argv:
        return
    total = build_timeline(lines, 3.0 if cast.get("title_mode") == "intro" else 1.2)
    print(f"② 音を合成（長さ {total:.1f} 秒）"); audio = mix_audio(lines, total, cast)
    print("③ 映像を合成"); render(lines, total, cast, audio, out)
    print("④ クレジット"); print(write_credits(lines, out.with_name(out.stem + "_credits.txt")))
    print(f"完成: {out}")


if __name__ == "__main__":
    main()
