"""台本から動画を1本作る。
使い方:  python3 tools/make_video.py [台本.json] [出力.mp4]
  省略時: script/script.json → output/video.mp4
手順: ①VOICEVOXで音声生成（変更のないセリフは再利用） ②音を合成 ③絵を合成 ④MP4に書き出し
"""
import hashlib, json, re, subprocess, sys, wave, urllib.request, urllib.parse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent
W, H, FPS, SR = 1080, 1920, 30, 48000
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
API = "http://localhost:50021"

GAP = 0.32          # セリフ間の基本の間（秒）
PAUSE = 1.3         # effect "pause" で追加する間（秒）
SILENT_DEFAULT = 1.5
TAIL = 2.0          # 最後の余韻


# ---------------- 音声 ----------------
def api(path, params, body=None):
    url = f"{API}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def tts_text(text):
    return re.sub(r"（[^）]*）|\([^)]*\)", "", text).strip()


def is_silent(text):
    return re.sub(r"[…・。、ー！？!?\.\s「」]", "", tts_text(text)) == ""


def read_wav(path):
    with wave.open(str(path)) as w:
        sr, ch = w.getframerate(), w.getnchannels()
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    if ch == 2:
        x = x.reshape(-1, 2).mean(1)
    if sr != SR:  # 線形補間でリサンプル
        n = int(len(x) * SR / sr)
        x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)
    return x


def make_voices(lines, cast):
    vdir = ROOT / "voices"; vdir.mkdir(exist_ok=True)
    for i, ln in enumerate(lines):
        if is_silent(ln["text"]):
            ln["wav"] = None; continue
        vid = ln.get("voice_id", cast["characters"][ln["speaker"]]["voice_id"])
        ln["voice_id"] = vid
        opts = dict(speed=ln.get("speed", cast.get("speed", 1.0)), volume=ln.get("volume", 1.0), pitch=ln.get("pitch", 0.0))
        key = hashlib.md5(json.dumps([tts_text(ln["text"]), ln.get("yomi"), vid, opts], ensure_ascii=False).encode()).hexdigest()[:8]
        out = vdir / f"{i + 1:02d}_{ln['speaker']}_{key}.wav"
        ln["wav"] = out
        if out.exists():
            continue
        for old in vdir.glob(f"{i + 1:02d}_*.wav"):
            old.unlink()
        q = json.loads(api("/audio_query", {"text": ln.get("yomi") or tts_text(ln["text"]), "speaker": vid}))
        q.update(speedScale=opts["speed"], volumeScale=opts["volume"], pitchScale=opts["pitch"],
                 prePhonemeLength=0.05, postPhonemeLength=0.08, outputSamplingRate=SR)
        out.write_bytes(api("/synthesis", {"speaker": vid}, json.dumps(q).encode()))
        print(f"  音声 {i + 1:02d} {ln['speaker']}「{ln['text']}」")


# ---------------- タイミング ----------------
def effects(ln):
    e = ln.get("effect", "none")
    return set([e] if isinstance(e, str) else e)


def build_timeline(lines):
    t = 0.4
    for ln in lines:
        fx = effects(ln)
        t += GAP + (PAUSE if "pause" in fx else 0)
        ln["start"] = t
        if ln["wav"]:
            ln["audio"] = read_wav(ln["wav"])
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


def load_char(name, c):
    imgs = {}
    for st in ("close", "open"):
        im = Image.open(ROOT / "assets/characters" / name / f"{st}.png").convert("RGBA")
        # 立ち絵の幅を 560px 基準にそろえる
        s = 560 * c.get("scale", 1.0) / im.width
        imgs[st] = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    dark = {k: ImageEnhance.Brightness(v).enhance(0.72) for k, v in imgs.items()}
    return imgs, dark


def compose_scene(bg, chars, cast, speaker, mouth_open):
    im = bg.copy()
    order = sorted(cast["characters"].items(), key=lambda kv: kv[1].get("layer", 0))
    for name, c in order:
        imgs, dark = chars[name]
        active = speaker is None or name == speaker
        st = "open" if (name == speaker and mouth_open) else "close"
        src = (imgs if active else dark)[st]
        im.alpha_composite(src, (int(c["x"] - src.width / 2), int(c["bottom"] - src.height)))
    return im.convert("RGB")


def face_point(name, cast, chars):
    c = cast["characters"][name]; h = chars[name][0]["close"].height
    return c["x"], c["bottom"] - h * 0.68


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
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = ImageFont.truetype(FONT, 78); fn = ImageFont.truetype(FONT, 44)
    rows = wrap(text, f, W - 120, d)
    lh = 100; top = 1430
    d.rounded_rectangle([30, top - 90, W - 30, top + lh * max(len(rows), 2) + 30], radius=36, fill=(0, 0, 0, 150))
    nw = d.textlength(speaker, font=fn)
    d.rounded_rectangle([60, top - 70, 60 + nw + 50, top - 6], radius=30, fill=hex2rgb(color) + (255,))
    d.text((85, top - 72), speaker, font=fn, fill="white")
    for i, r in enumerate(rows):
        tw = d.textlength(r, font=f)
        d.text(((W - tw) / 2, top + i * lh), r, font=f, fill="white", stroke_width=9, stroke_fill=hex2rgb(color))
    return layer


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
    bg = Image.open(ROOT / cast["background"]).convert("RGBA").resize((W, H), Image.LANCZOS)
    chars = {n: load_char(n, c) for n, c in cast["characters"].items()}

    # フレームごとの「今のセリフ」
    cur = [-1] * nframes
    for i, ln in enumerate(lines):
        s = int(ln["start"] * FPS)
        e = int(lines[i + 1]["start"] * FPS) if i + 1 < len(lines) else nframes
        for f in range(s, min(e, nframes)):
            cur[f] = i
    mouths = [mouth_track(ln, nframes) for ln in lines]

    scene_cache, sub_cache = {}, {}
    title = title_layer(cast["title"])
    rng = np.random.default_rng(1)
    cx, cy, z = W / 2, H / 2, 1.0

    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(audio),
                           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
                          stdin=subprocess.PIPE)
    for f in range(nframes):
        i = cur[f]
        ln = lines[i] if i >= 0 else None
        spk = ln["speaker"] if ln else None
        mo = bool(mouths[i][f]) if ln else False
        key = (spk, mo)
        if key not in scene_cache:
            scene_cache[key] = compose_scene(bg, chars, cast, spk, mo)
        scene = scene_cache[key]

        # カメラ（ズーム・揺れ）
        fx = effects(ln) if ln else set()
        tz, tx, ty = 1.0, W / 2, H / 2
        if "zoom" in fx:
            tz = 1.25
            tx, ty = face_point(spk, cast, chars)
        k = 0.35
        z += (tz - z) * k; cx += (tx - cx) * k; cy += (ty - cy) * k
        zz, sx, sy = z, 0.0, 0.0
        if "shake" in fx:
            el = f / FPS - ln["start"]
            if 0 <= el < 0.6:
                amp = 28 * (1 - el / 0.6)
                sx, sy = rng.uniform(-amp, amp, 2)
                zz = max(zz, 1.06)
        bw, bh = W / zz, H / zz
        x0 = min(max(cx - bw / 2 + sx, 0), W - bw); y0 = min(max(cy - bh / 2 + sy, 0), H - bh)
        frame = scene.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + bw, y0 + bh)) if zz > 1.001 else scene
        frame = frame.convert("RGBA")
        frame.alpha_composite(title)
        if ln:
            if i not in sub_cache:
                sub_cache[i] = subtitle_layer(spk, ln["text"], cast["characters"][spk]["color"])
            frame.alpha_composite(sub_cache[i])
        ff.stdin.write(frame.convert("RGB").tobytes())
        if f % 150 == 0:
            print(f"  映像 {f}/{nframes} フレーム", end="\r")
    ff.stdin.close(); ff.wait()
    print()


def write_credits(lines, out):
    try:
        sp = json.loads(urllib.request.urlopen(f"{API}/speakers", timeout=10).read())
        idname = {st["id"]: s["name"] for s in sp for st in s["styles"]}
    except Exception:
        idname = {}
    names = []
    for ln in lines:
        n = idname.get(ln.get("voice_id"))
        if n and n not in names:
            names.append(n)
    txt = "【概要欄用クレジット】\n" + "\n".join(f"VOICEVOX:{n}" for n in names) + \
          "\n\n（効果音・BGMは自作の合成音）\n"
    out.write_text(txt, encoding="utf-8")
    return txt


def main():
    script = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "script/script.json"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "output/video.mp4"
    cast = json.loads((ROOT / "script/cast.json").read_text())
    lines = json.loads(Path(script).read_text())
    print("① 音声を作成"); make_voices(lines, cast)
    total = build_timeline(lines)
    print(f"② 音を合成（長さ {total:.1f} 秒）"); audio = mix_audio(lines, total, cast)
    print("③ 映像を合成"); render(lines, total, cast, audio, out)
    print("④ クレジット"); print(write_credits(lines, out.with_name(out.stem + "_credits.txt")))
    print(f"完成: {out}")


if __name__ == "__main__":
    main()
