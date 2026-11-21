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
            ln["engine"] = "sbv2"
            opts = ["sbv2", c["model"], ln.get("emotion", c.get("emotion", "ふつう")),
                    ln.get("strength", c.get("strength", 2.0)), speed, volume]
        else:
            vid = ln.get("voice_id", c["voice_id"]); ln["voice_id"] = vid
            opts = ["vv", vid, speed, volume, ln.get("pitch", 0.0)]
        key = hashlib.md5(json.dumps([text, opts], ensure_ascii=False).encode()).hexdigest()[:8]
        out = vdir / f"{i + 1:02d}_{ln['speaker']}_{key}.wav"
        ln["wav"] = out
        if out.exists():
            continue
        for old in vdir.glob(f"{i + 1:02d}_*.wav"):
            old.unlink()
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


def build_timeline(lines):
    t = 1.2  # 最初はタイトルと背景だけ見せる
    for ln in lines:
        fx = effects(ln)
        t += GAP + (PAUSE if "pause" in fx else 0)
        ln["start"] = t
        if ln["wav"]:
            ln["audio"] = read_wav(ln["wav"])
            if ln.get("muffle"):  # 壁ごしの声（こもった音）
                k = np.ones(14) / 14
                ln["audio"] = np.convolve(np.convolve(ln["audio"], k, "same"), k, "same") * 0.9
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


def cover(im, w=W, h=H):
    """画面いっぱいに拡大して中央を切り抜く"""
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def load_img(path):
    return cover(Image.open(path).convert("RGB")) if path.exists() else None


class Shots:
    """カット（場面）ごとの絵を読み込んでおく"""
    def __init__(self, cast):
        self.cast = cast; self.cache = {}

    def get(self, key):
        if key in self.cache:
            return self.cache[key]
        kind, name, mouth = key
        if kind == "char":
            d = ROOT / "assets/characters" / name
            im = load_img(d / f"{mouth}.png") or load_img(d / "close.png")
        elif kind == "shot":
            im = load_img(ROOT / "assets/shots" / f"{name}.png")
        else:
            im = load_img(ROOT / self.cast["background"])
        self.cache[key] = im or Image.new("RGB", (W, H), (60, 60, 60))
        return self.cache[key]


def shot_key(ln, mouth_open):
    if ln is None:
        return ("bg", None, None)
    if ln.get("shot"):
        return ("shot", ln["shot"], None)
    return ("char", ln["speaker"], "open" if mouth_open else "close")


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
    f = ImageFont.truetype(FONT, 80)
    rows = wrap(text, f, W - 100, d)
    lh = 104; top = 1560 - lh * len(rows)
    for i, r in enumerate(rows):
        tw = d.textlength(r, font=f); x, y = (W - tw) / 2, top + i * lh
        d.text((x, y), r, font=f, fill="black", stroke_width=16, stroke_fill="black")
        d.text((x, y), r, font=f, fill="white", stroke_width=9, stroke_fill=hex2rgb(color))
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
    shots = Shots(cast)
    cur = [-1] * nframes
    for i, ln in enumerate(lines):
        s = int(ln["start"] * FPS)
        e = int(lines[i + 1]["start"] * FPS) if i + 1 < len(lines) else nframes
        for f in range(s, min(e, nframes)):
            cur[f] = i
    mouths = [mouth_track(ln, nframes) for ln in lines]
    sub_cache = {}
    title = title_layer(cast["title"])
    rng = np.random.default_rng(1)
    z, prev_shot, shot_start = 1.0, None, 0

    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(audio),
                           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
                          stdin=subprocess.PIPE)
    for f in range(nframes):
        i = cur[f]
        ln = lines[i] if i >= 0 else None
        key = shot_key(ln, bool(mouths[i][f]) if ln else False)
        scene = shots.get(key)
        shot_id = key[:2]
        if shot_id != prev_shot:          # カットが変わったらカメラをリセット
            prev_shot, shot_start, z = shot_id, f, 1.0
        fx = effects(ln) if ln else set()
        # ゆっくり寄っていく動き＋ズーム演出
        drift = 1.0 + 0.0015 * (f - shot_start)
        tz = 1.22 if "zoom" in fx else 1.0
        z += (tz - z) * 0.3
        zz = max(1.0, min(z * min(drift, 1.08), 1.4))
        cx, cy = W / 2, H * 0.36           # 顔のあたりに向かって寄る
        sx = sy = 0.0
        if "shake" in fx:
            el = f / FPS - ln["start"]
            if 0 <= el < 0.6:
                amp = 30 * (1 - el / 0.6)
                sx, sy = rng.uniform(-amp, amp, 2)
                zz = max(zz, 1.08)
        bw, bh = W / zz, H / zz
        x0 = min(max(cx - bw / 2 + sx, 0), W - bw); y0 = min(max(cy - bh / 2 + sy, 0), H - bh)
        frame = scene.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + bw, y0 + bh)) if zz > 1.001 else scene
        frame = frame.convert("RGBA")
        frame.alpha_composite(title)
        if ln:
            if i not in sub_cache:
                sub_cache[i] = subtitle_layer(ln["speaker"], ln["text"], cast["characters"][ln["speaker"]]["color"])
            frame.alpha_composite(sub_cache[i])
        ff.stdin.write(frame.convert("RGB").tobytes())
        if f % 150 == 0:
            print(f"  映像 {f}/{nframes} フレーム", end="\r")
    ff.stdin.close(); ff.wait()
    print()


def write_credits(lines, out):
    names, sbv = [], False
    try:
        sp = json.loads(urllib.request.urlopen(f"{API}/speakers", timeout=10).read())
        idname = {st["id"]: s["name"] for s in sp for st in s["styles"]}
    except Exception:
        idname = {}
    for ln in lines:
        if ln.get("engine") == "sbv2":
            sbv = True
        n = idname.get(ln.get("voice_id")) if ln.get("engine") != "sbv2" else None
        if n and n not in names:
            names.append(n)
    rows = [f"VOICEVOX:{n}" for n in names]
    if sbv:
        rows += ["音声合成：Style-Bert-VITS2", "音声モデル：JVNV (CC BY-SA 4.0) https://sites.google.com/site/shinnosuketakamichi/research-topics/jvnv_corpus"]
    rows += ["画像生成：Animagine XL 4.0", "効果音・BGM：自作"]
    txt = "【概要欄用クレジット】\n" + "\n".join(rows) + "\n"
    out.write_text(txt, encoding="utf-8")
    return txt


def main():
    script = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "script/script.json"
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "output/video.mp4"
    cast = json.loads((ROOT / "script/cast.json").read_text())
    data = json.loads(Path(script).read_text())
    if isinstance(data, dict):  # {"title": ..., "lines": [...]} 形式（回ごとにタイトルを持てる）
        cast["title"] = data.get("title", cast["title"]); lines = data["lines"]
    else:
        lines = data
    print("① 音声を作成"); make_voices(lines, cast)
    total = build_timeline(lines)
    print(f"② 音を合成（長さ {total:.1f} 秒）"); audio = mix_audio(lines, total, cast)
    print("③ 映像を合成"); render(lines, total, cast, audio, out)
    print("④ クレジット"); print(write_credits(lines, out.with_name(out.stem + "_credits.txt")))
    print(f"完成: {out}")


if __name__ == "__main__":
    main()
