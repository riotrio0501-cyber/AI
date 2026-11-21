"""声の見本動画を作る（番号つき）。 python3 tools/voice_catalog.py → output/voice_catalog.mp4"""
import json, subprocess, sys, urllib.request, urllib.parse
from pathlib import Path
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sbv2

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / "output/_catalog"; TMP.mkdir(parents=True, exist_ok=True)
F = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
SR = 48000
T1, T2 = "はじめまして。今日はよろしくお願いします。", "芋煮は醤油に決まってるでしょ！"

# (表示名, 説明, 種類, 指定)
V = [
 ("JVNV M1", "男性・若め（今の彼氏）", "sbv2", ("jvnv-M1-jp", "Angry")),
 ("JVNV M2", "男性（今の父）", "sbv2", ("jvnv-M2-jp", "Angry")),
 ("JVNV F1", "女性（今の娘）", "sbv2", ("jvnv-F1-jp", "Angry")),
 ("JVNV F2", "女性（今の母）", "sbv2", ("jvnv-F2-jp", "Angry")),
 ("Lux", "女性・感情指定なし", "sbv2", ("lux", "Neutral")),
 ("zonoko", "女性・表記不要", "sbv2", ("zonoko", "Neutral")),
 ("あみたろ", "女性・配信風", "sbv2", ("amitaro", "Neutral")),
 ("小春音アミ", "女性・明るい", "sbv2", ("koharune-ami", "るんるん")),
 ("青山龍星", "男性・渋い（VOICEVOX）", "vv", (13, 82)),
 ("麒ヶ島宗麟", "男性・年配（VOICEVOX）", "vv", (53, 53)),
 ("ちび式じい", "男性・おじいちゃん（VOICEVOX）", "vv", (42, 42)),
 ("玄野武宏", "男性・青年（VOICEVOX）", "vv", (11, 40)),
 ("白上虎太郎", "男性・少年っぽい（VOICEVOX）", "vv", (12, 34)),
 ("剣崎雌雄", "男性・低め（VOICEVOX）", "vv", (21, 21)),
 ("雀松朱司", "男性・落ち着き（VOICEVOX）", "vv", (52, 52)),
 ("黒沢冴白", "男性（VOICEVOX）", "vv", (100, 100)),
 ("離途", "男性・クール（VOICEVOX）", "vv", (99, 101)),
 ("冥鳴ひまり", "女性・落ち着き（VOICEVOX）", "vv", (14, 14)),
 ("春日部つむぎ", "女性・元気（VOICEVOX）", "vv", (8, 8)),
 ("四国めたん", "女性・お姉さん（VOICEVOX）", "vv", (2, 6)),
 ("九州そら", "女性・大人（VOICEVOX）", "vv", (16, 18)),
 ("もち子さん", "女性・やさしい（VOICEVOX）", "vv", (20, 78)),
 ("雨晴はう", "女性・看護師風（VOICEVOX）", "vv", (10, 10)),
 ("WhiteCUL", "女性（VOICEVOX）", "vv", (23, 24)),
 ("No.7", "女性・アナウンサー風（VOICEVOX）", "vv", (29, 29)),
 ("東北イタコ", "女性・大人（VOICEVOX）", "vv", (109, 109)),
 ("夜語トバリ", "女性・ミステリアス（VOICEVOX）", "vv", (118, 121)),
 ("暁記ミタマ", "女性（VOICEVOX）", "vv", (122, 123)),
 ("波音リツ", "女性・クール（VOICEVOX）", "vv", (9, 65)),
]


def vv(text, sid):
    u = "http://localhost:50021"
    q = urllib.request.urlopen(urllib.request.Request(f"{u}/audio_query?" + urllib.parse.urlencode({"text": text, "speaker": sid}), method="POST")).read()
    b = urllib.request.urlopen(urllib.request.Request(f"{u}/synthesis?speaker={sid}", data=q, method="POST", headers={"Content-Type": "application/json"})).read()
    p = TMP / "tmp.wav"; p.write_bytes(b)
    x, sr = sf.read(p, dtype="float32"); return sr, x


def res(sr, x):
    if x.ndim > 1: x = x.mean(1)
    x = np.interp(np.linspace(0, len(x) - 1, int(len(x) * SR / sr)), np.arange(len(x)), x).astype(np.float32)
    return x / max(1e-3, np.abs(x).max()) * 0.8


parts = []
for i, (name, desc, kind, (a, b)) in enumerate(V, 1):
    out = TMP / f"{i:02d}.mp4"
    if not out.exists():
        if kind == "sbv2":
            x1 = res(*sbv2.synth(T1, a, "Neutral")); x2 = res(*sbv2.synth(T2, a, b, strength=2.0 if a.startswith("jvnv") else 1.0))
        else:
            x1 = res(*vv(T1, a)); x2 = res(*vv(T2, b))
        z = lambda s: np.zeros(int(s * SR), np.float32)
        sf.write(TMP / "a.wav", np.concatenate([z(.3), x1, z(.4), x2, z(.7)]), SR)
        im = Image.new("RGB", (1080, 1080), (25, 25, 35)); d = ImageDraw.Draw(im)
        d.text((540, 330), f"{i}", font=ImageFont.truetype(F, 200), fill=(255, 220, 90), anchor="mm")
        d.text((540, 560), name, font=ImageFont.truetype(F, 90), fill="white", anchor="mm")
        d.text((540, 690), desc, font=ImageFont.truetype(F, 50), fill=(170, 200, 255), anchor="mm")
        im.save(TMP / "a.png")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", str(TMP / "a.png"), "-i", str(TMP / "a.wav"),
                        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-ar", "48000", "-shortest", str(out)], check=True)
        print(i, name, flush=True)
    parts.append(f"file '{out.name}'")
(TMP / "list.txt").write_text("\n".join(parts))
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-i", str(TMP / "list.txt"), "-c", "copy", str(ROOT / "output/voice_catalog.mp4")], check=True)
print("完成: output/voice_catalog.mp4")
