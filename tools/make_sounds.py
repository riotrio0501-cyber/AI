"""効果音とBGMを、プログラムで一から合成して作る（外部素材を使わないので権利の心配なし）。

使い方: python3 tools/make_sounds.py
  → assets/se/*.wav, assets/bgm/bouncy_pizzicato.wav を作り、assets/sound_credits.yaml に登録する。

「仮」と付いたもの（くしゃみなど）は合成では限界があるので、
後で商用OK素材に差し替える想定（差し替えたら sound_credits.yaml も書き換える）。
"""
from __future__ import annotations

import wave

import numpy as np
import yaml

from common import ASSETS

SR = 48000
rng = np.random.default_rng(7)


def t(sec):
    return np.arange(int(SR * sec)) / SR


def env(n, attack=0.005, release=None):
    e = np.ones(n)
    a = max(1, int(SR * attack))
    e[:a] = np.linspace(0, 1, a)
    if release:
        r = min(n, int(SR * release))
        e[-r:] *= np.linspace(1, 0, r)
    return e


def decay(sec, rate):
    return np.exp(-t(sec) * rate)


def noise(sec):
    return rng.standard_normal(int(SR * sec))


def bandpass(x, lo, hi):
    """FFTで帯域だけ残す簡易フィルタ。"""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def glide(f0, f1, sec, curve="exp"):
    """周波数を f0→f1 に変化させるサイン波。"""
    n = int(SR * sec)
    f = np.geomspace(f0, f1, n) if curve == "exp" else np.linspace(f0, f1, n)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def pad(x, sec):
    return np.concatenate([x, np.zeros(int(SR * sec))])


def mix(*parts):
    """(開始秒, 波形) のリストを重ねる。"""
    n = max(int(SR * s) + len(w) for s, w in parts)
    out = np.zeros(n)
    for s, w in parts:
        i = int(SR * s)
        out[i:i + len(w)] += w
    return out


def save(path, x, stereo=False):
    x = np.clip(x, -1, 1)
    data = (x * 32767).astype(np.int16)
    if stereo:
        data = data.reshape(-1, 2)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2 if stereo else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# ---------------- 効果音 ----------------
def se_wind_blizzard():
    sec = 6
    x = bandpass(noise(sec), 250, 2500)
    lfo = 0.55 + 0.45 * np.sin(2 * np.pi * 0.35 * t(sec)) * np.sin(2 * np.pi * 0.13 * t(sec) + 1)
    hiss = bandpass(noise(sec), 3000, 9000) * 0.15
    return norm((x * lfo + hiss) * env(int(SR * sec), 0.8, 1.0), 0.6)


def se_sparkle():
    notes = [1568, 2093, 2637, 3136, 4186]
    parts = [(i * 0.06, (np.sin(2 * np.pi * f * t(0.7)) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t(0.7))) * decay(0.7, 7))
             for i, f in enumerate(notes)]
    return norm(mix(*parts), 0.7)


def se_sneeze_temp():
    # 「ハ…ハ…」息を吸う音 → 「ックション」破裂。合成なので仮。
    def breath(sec, lo, hi):
        return bandpass(noise(sec), lo, hi) * env(int(SR * sec), 0.15, 0.1)
    choo = bandpass(noise(0.45), 600, 5000) * decay(0.45, 9)
    thump = np.sin(2 * np.pi * 110 * t(0.2)) * decay(0.2, 25)
    return norm(mix((0, breath(0.25, 800, 2500) * 0.4), (0.4, breath(0.3, 900, 3000) * 0.6),
                    (0.85, choo), (0.85, thump * 0.6)), 0.85)


def se_whoosh():
    sec = 0.6
    n = noise(sec)
    out = np.zeros_like(n)
    for k, (lo, hi) in enumerate([(300, 900), (600, 1800), (1200, 3500), (2000, 6000)]):
        seg = bandpass(n, lo, hi)
        out += seg * np.exp(-((t(sec) - 0.12 - k * 0.08) / 0.09) ** 2)
    return norm(out, 0.7)


def se_ice_slide():
    sec = 2.2
    x = bandpass(noise(sec), 2500, 8000) * 0.5 + glide(1800, 1400, sec) * 0.05
    return norm(x * env(int(SR * sec), 0.05, 1.5), 0.45)


def se_slip():
    up = glide(300, 1800, 0.25) * env(int(SR * 0.25), 0.005, 0.03)
    return norm(up, 0.7)


def se_boing():
    sec = 0.8
    f = 180 * (1 + 0.5 * np.exp(-t(sec) * 4) * np.sin(2 * np.pi * 14 * t(sec)))
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * decay(sec, 4)
    return norm(x, 0.8)


def se_roll_rumble():
    sec = 4.0
    x = bandpass(noise(sec), 40, 300)
    bumps = (np.sin(2 * np.pi * 6 * t(sec)) > 0.9).astype(float) * 0.6 + 0.6
    clicks = bandpass(noise(sec), 2000, 6000) * 0.08
    return norm((x * bumps + clicks) * env(int(SR * sec), 0.2, 0.6), 0.75)


def se_pat():
    thud = np.sin(2 * np.pi * 140 * t(0.12)) * decay(0.12, 35)
    slap = bandpass(noise(0.05), 400, 2500) * decay(0.05, 80)
    return norm(mix((0, thud), (0, slap * 0.6)), 0.8)


def se_crash():
    boom = np.sin(2 * np.pi * np.cumsum(np.geomspace(120, 35, int(SR * 1.2))) / SR) * decay(1.2, 3.5)
    burst = bandpass(noise(1.5), 200, 6000) * decay(1.5, 4)
    return norm(mix((0, boom), (0, burst * 0.7)), 0.95)


def se_wood_crack():
    parts = []
    for i in range(14):
        s = i * 0.09 + rng.uniform(0, 0.05)
        f = rng.uniform(250, 700)
        knock = (np.sin(2 * np.pi * f * t(0.18)) + bandpass(noise(0.18), 800, 4000) * 0.6) * decay(0.18, 30)
        parts.append((s, knock * (1 - i / 16)))
    return norm(mix(*parts), 0.75)


def se_drop_tiny():
    x = np.sin(2 * np.pi * 900 * t(0.15)) * decay(0.15, 40)
    return norm(mix((0, x), (0.18, x * 0.35)), 0.6)


def se_water_rush():
    sec = 2.5
    x = bandpass(noise(sec), 150, 4000)
    swell = np.minimum(1, t(sec) / 0.6) * np.exp(-np.maximum(0, t(sec) - 1.4) * 2.5)
    return norm(x * swell, 0.8)


def se_freeze():
    sec = 1.4
    crackle = np.zeros(int(SR * sec))
    for _ in range(140):
        i = rng.integers(0, int(SR * 0.9))
        crackle[i:i + 200] += rng.uniform(-1, 1) * decay(200 / SR, 600)[:len(crackle[i:i + 200])]
    shimmer = glide(5000, 2500, sec) * decay(sec, 3) * 0.25
    hit = mix((0.95, np.sin(2 * np.pi * 2637 * t(0.4)) * decay(0.4, 10) * 0.6))
    return norm(mix((0, crackle), (0, shimmer), (0, hit)), 0.85)


def se_waddle():
    steps = [(i * 0.28, bandpass(noise(0.06), 300, 1500) * decay(0.06, 60) * (0.8 if i % 2 else 1)) for i in range(10)]
    return norm(mix(*steps), 0.6)


def se_pop():
    x = glide(500, 1400, 0.06) * env(int(SR * 0.06), 0.002, 0.02)
    return norm(x, 0.7)


def se_gulp():
    x = glide(420, 140, 0.18) * env(int(SR * 0.18), 0.005, 0.06)
    return norm(mix((0, x), (0.22, glide(300, 110, 0.12) * env(int(SR * 0.12), 0.005, 0.05) * 0.6)), 0.8)


def se_tink():
    sec = 2.5
    f = 3520
    x = (np.sin(2 * np.pi * f * t(sec)) + 0.4 * np.sin(2 * np.pi * f * 2.4 * t(sec)) * decay(sec, 6)) * decay(sec, 1.8)
    return norm(x, 0.7)


SOUNDS = {
    "wind_blizzard": (se_wind_blizzard, "吹雪の風"),
    "sparkle": (se_sparkle, "キラーン"),
    "sneeze_temp": (se_sneeze_temp, "くしゃみ（仮。差し替え推奨）"),
    "whoosh": (se_whoosh, "ヒュッ"),
    "ice_slide": (se_ice_slide, "氷の上をシャーッ"),
    "slip": (se_slip, "ツルッ"),
    "boing": (se_boing, "ビヨーン"),
    "roll_rumble": (se_roll_rumble, "ゴロゴロ"),
    "pat": (se_pat, "ポン"),
    "crash": (se_crash, "ドカーン"),
    "wood_crack": (se_wood_crack, "木がバキバキ"),
    "drop_tiny": (se_drop_tiny, "ポトッ"),
    "water_rush": (se_water_rush, "ザバーッ"),
    "freeze": (se_freeze, "ピキピキッ（凍る）"),
    "waddle": (se_waddle, "ペタペタ（足音）"),
    "pop": (se_pop, "パクッ"),
    "gulp": (se_gulp, "ゴクン"),
    "tink": (se_tink, "チーン（涙）"),
}


# ---------------- BGM ----------------
def pluck(freq, sec, bright=1.0):
    tt = t(sec)
    x = sum((bright ** k) / k * np.sin(2 * np.pi * freq * k * tt) for k in range(1, 6))
    return x * np.exp(-tt * 9) * env(len(tt), 0.003)


def tuba(freq, sec):
    tt = t(sec)
    x = np.sin(2 * np.pi * freq * tt) + 0.5 * np.sin(2 * np.pi * freq * 2 * tt) + 0.2 * np.sin(2 * np.pi * freq * 3 * tt)
    return x * env(len(tt), 0.02, sec * 0.6)


def block(sec=0.08, f=1100):
    return np.sin(2 * np.pi * f * t(sec)) * decay(sec, 70)


def midi(n):
    return 440 * 2 ** ((n - 69) / 12)


def bgm_bouncy_pizzicato(total=60.0):
    """オリジナルのコミカルなピチカート曲（112BPM、8小節ループ）。"""
    bpm = 112
    beat = 60 / bpm
    # コード進行（ベースのルート音, 和音）: C F G C / Am Dm G7 C
    prog = [(48, [60, 64, 67]), (53, [60, 65, 69]), (55, [59, 62, 67]), (48, [60, 64, 67]),
            (45, [60, 64, 69]), (50, [62, 65, 69]), (55, [59, 62, 65]), (48, [60, 64, 67])]
    # メロディ（8分音符単位、Noneは休み）
    mel = [72, None, 76, 79, 77, None, 76, 74,  77, None, 81, 77, 76, 74, 72, None,
           74, 76, 77, 79, 77, 74, 71, None,     72, 76, 79, 84, 79, None, None, None,
           69, None, 72, 76, 74, 72, 69, None,   74, None, 77, 81, 79, 77, 74, None,
           79, 77, 76, 74, 71, 74, 77, 74,       72, None, 67, None, 72, None, None, None]
    loop_sec = 8 * 4 * beat
    parts = []
    reps = int(np.ceil(total / loop_sec))
    for r in range(reps):
        base = r * loop_sec
        for bar, (root, chord) in enumerate(prog):
            b0 = base + bar * 4 * beat
            for k in range(4):  # ベース: 1・3拍がルート、2・4拍が5度
                note = root if k % 2 == 0 else root + 7
                parts.append((b0 + k * beat, tuba(midi(note), beat * 0.7) * 0.35))
                parts.append((b0 + k * beat + beat / 2, sum(pluck(midi(c), beat * 0.4, 0.5) for c in chord) * 0.12))
                parts.append((b0 + k * beat, block(f=1300 if k % 2 else 900) * 0.18))
            for i in range(8):
                n = mel[bar * 8 + i]
                if n is not None:
                    parts.append((b0 + i * beat / 2, pluck(midi(n), beat * 0.9, 0.7) * 0.32))
    x = mix(*parts)[: int(SR * total)]
    x = norm(x, 0.85)
    # 簡単なステレオ広がり（右だけ少し遅らせる）
    d = int(SR * 0.012)
    right = np.concatenate([np.zeros(d), x[:-d]])
    st = np.stack([x, 0.85 * right + 0.15 * x], axis=1).reshape(-1)
    return st


def main():
    se_dir, bgm_dir = ASSETS / "se", ASSETS / "bgm"
    se_dir.mkdir(parents=True, exist_ok=True)
    bgm_dir.mkdir(parents=True, exist_ok=True)
    credits_path = ASSETS / "sound_credits.yaml"
    credits = yaml.safe_load(credits_path.read_text(encoding="utf-8")) if credits_path.exists() else {}
    credits = credits or {}
    own = {"author": "自作（tools/make_sounds.py で合成）", "source": "このリポジトリ", "license": "自作のため制限なし",
           "commercial_use": True, "credit_required": False}
    for name, (fn, desc) in SOUNDS.items():
        save(se_dir / f"{name}.wav", pad(fn(), 0.05))
        credits[f"se/{name}.wav"] = {"title": desc, **own}
    save(bgm_dir / "bouncy_pizzicato.wav", bgm_bouncy_pizzicato(), stereo=True)
    credits["bgm/bouncy_pizzicato.wav"] = {"title": "コミカルなピチカート（オリジナル曲）", **own}
    credits_path.write_text(yaml.safe_dump(credits, allow_unicode=True, sort_keys=True), encoding="utf-8")
    print(f"効果音 {len(SOUNDS)} 個と BGM 1 曲を作りました → assets/se, assets/bgm")


if __name__ == "__main__":
    main()
