#!/usr/bin/env python3
"""効果音とBGMを数式で自作する（著作権・クレジット表記の心配なし）。

使い方:  python3 tools/make_sfx.py
出力先:  assets/se/*.wav, assets/bgm/*.wav
"""
import os
import wave

import numpy as np

SR = 44100
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rng = np.random.default_rng(7)


def t_axis(sec):
    return np.arange(int(SR * sec)) / SR


def env(n, a=0.005, r=0.1, sustain=1.0):
    """attack / release の簡単な音量カーブ"""
    e = np.ones(n) * sustain
    na, nr = max(1, int(SR * a)), max(1, int(SR * r))
    e[:na] = np.linspace(0, sustain, na)
    if nr < n:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def sweep(f0, f1, sec, shape="sin"):
    t = t_axis(sec)
    f = np.geomspace(f0, f1, len(t))
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) if shape == "sin" else np.sign(np.sin(ph)) * 0.5


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def noise(sec):
    return rng.uniform(-1, 1, int(SR * sec))


def norm(x, peak=0.9):
    m = np.max(np.abs(x)) or 1
    return x / m * peak


def save(path, x):
    x = np.clip(x, -1, 1)
    data = (x * 32767).astype(np.int16)
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


# ---------------- 効果音 ----------------

def snore():
    """大いびき：吸う（ゴゴゴ）→吐く（鼻ちょうちんがふくらむ「ぷぅ〜」）"""
    t = t_axis(1.1)
    buzz = np.sign(np.sin(2 * np.pi * (55 + 8 * np.sin(2 * np.pi * 3 * t)) * t))
    buzz = lowpass(buzz * (0.6 + 0.4 * noise(1.1)), 900)
    inhale = buzz * np.sin(np.pi * t / 1.1) ** 1.5
    whistle = sweep(500, 1100, 0.9) * 0.35 * np.sin(np.pi * t_axis(0.9) / 0.9)
    return norm(np.concatenate([inhale, np.zeros(int(SR * 0.05)), whistle]))


def small_snore():
    t = t_axis(0.8)
    x = sweep(900, 1400, 0.8) * 0.5 + lowpass(noise(0.8), 2500) * 0.2
    return norm(x * np.sin(np.pi * t / 0.8) ** 2, 0.6)


def pop_in():
    x = sweep(300, 1200, 0.08) * env(int(SR * 0.08), 0.002, 0.05)
    return norm(x, 0.7)


def whoosh():
    n = noise(0.35)
    t = t_axis(0.35)
    x = lowpass(n, 1800) * np.sin(np.pi * t / 0.35) ** 2
    return norm(x, 0.7)


def tada():
    """ドヤ顔の「キラーン」"""
    out = np.zeros(int(SR * 0.9))
    for i, f in enumerate([1318, 1568, 2093, 2637]):
        s = int(SR * 0.06 * i)
        t = t_axis(0.9 - 0.06 * i)
        tone = np.sin(2 * np.pi * f * t) * np.exp(-t * 6)
        out[s:s + len(tone)] += tone
    return norm(out, 0.7)


def tick():
    """時計のチク・タク"""
    out = np.zeros(int(SR * 0.6))
    for i, f in enumerate([3200, 2400]):
        t = t_axis(0.03)
        c = np.sin(2 * np.pi * f * t) * np.exp(-t * 200) + noise(0.03) * np.exp(-t * 300) * 0.3
        s = int(SR * 0.5 * i / 1.0)
        out[s:s + len(c)] += c
    return norm(out, 0.6)


def alarm():
    """目覚まし時計10個が同時に鳴る（ジリリリ…）。少しずつずらして混ぜる"""
    dur = 4.6
    t = t_axis(dur)
    out = np.zeros_like(t)
    for k in range(10):
        f = rng.uniform(1800, 3200)
        rate = rng.uniform(16, 24)  # 叩く速さ
        bell = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t)
        hammer = (np.sin(2 * np.pi * rate * t + rng.uniform(0, 6)) > 0).astype(float)
        hammer = lowpass(hammer, 80)
        start = int(SR * rng.uniform(0, 0.12))
        piece = bell * hammer
        piece[:start] = 0
        out += piece
    out *= env(len(out), 0.01, 0.25)
    return norm(out, 0.8)


def rustle_thud():
    """寝返り：もぞもぞ→ドスン"""
    r = lowpass(noise(0.5), 1200) * np.sin(np.pi * t_axis(0.5) / 0.5)
    t = t_axis(0.4)
    thud = np.sin(2 * np.pi * (70 * np.exp(-t * 4)) * t) * np.exp(-t * 9)
    return norm(np.concatenate([r * 0.5, thud]))


def clang():
    """フライパンを叩く（ゴワァーン）"""
    t = t_axis(0.9)
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) * a
            for f, d, a in [(523, 4, 1), (1240, 6, 0.7), (2310, 9, 0.5), (3570, 12, 0.3)])
    x += noise(0.9) * np.exp(-t * 60) * 0.6
    return norm(x, 0.8)


def deflate():
    """力尽きる「ひゅるる〜」"""
    x = sweep(900, 180, 0.8, "sin") * env(int(SR * 0.8), 0.01, 0.3)
    vib = 1 + 0.3 * np.sin(2 * np.pi * 9 * t_axis(0.8))
    return norm(x * vib, 0.6)


def eye_pop():
    """パチッ！"""
    t = t_axis(0.15)
    x = sweep(600, 2400, 0.06) * env(int(SR * 0.06), 0.001, 0.03)
    c = noise(0.15) * np.exp(-t * 80)
    out = np.zeros(int(SR * 0.15))
    out[:len(x)] += x
    out += c * 0.5
    return norm(out, 0.9)


def slide_down():
    """大あくびに合わせたスライドホイッスル"""
    t = t_axis(1.3)
    x = sweep(1200, 300, 1.3) * (1 + 0.2 * np.sin(2 * np.pi * 6 * t))
    return norm(x * env(len(t), 0.05, 0.3), 0.6)


def tumble():
    """ころころ転がる→ボヨン"""
    out = []
    for i in range(6):
        t = t_axis(0.12)
        out.append(np.sin(2 * np.pi * (220 + 40 * i) * t) * np.exp(-t * 30))
    t = t_axis(0.5)
    boing = np.sin(2 * np.pi * (180 + 120 * np.sin(2 * np.pi * 14 * t) * np.exp(-t * 4)) * t) * np.exp(-t * 5)
    return norm(np.concatenate(out + [boing]))


def snow_poof():
    """雪に「ぼふっ」と埋まる"""
    t = t_axis(0.6)
    x = lowpass(noise(0.6), 700) * np.exp(-t * 7)
    x += np.sin(2 * np.pi * 60 * t) * np.exp(-t * 12) * 0.8
    return norm(x)


def sneeze():
    """特大くしゃみ：ハッ…ハッ…ブシュン！（声ではなく音で）"""
    a = lowpass(noise(0.25), 3000) * np.sin(np.pi * t_axis(0.25) / 0.25) * 0.3
    t = t_axis(0.5)
    b = (lowpass(noise(0.5), 5000) * np.exp(-t * 9) + np.sin(2 * np.pi * 90 * t) * np.exp(-t * 14)) * 1.0
    return norm(np.concatenate([a, np.zeros(int(SR * 0.15)), a, np.zeros(int(SR * 0.2)), b]))


def shutter():
    """スマホのシャッター「カシャッ」"""
    t = t_axis(0.18)
    c1 = noise(0.04) * np.exp(-t_axis(0.04) * 150)
    c2 = lowpass(noise(0.08), 4000) * np.exp(-t_axis(0.08) * 60)
    out = np.zeros(len(t))
    out[:len(c1)] += c1
    s = int(SR * 0.07)
    out[s:s + len(c2)] += c2
    return norm(out, 0.8)


def rumble():
    """雪崩・大玉のゴゴゴゴ"""
    t = t_axis(3.0)
    x = lowpass(noise(3.0), 200) * 3 + lowpass(noise(3.0), 900) * 0.4
    return norm(x * env(len(t), 0.6, 0.8))


def wind():
    """猛吹雪のビューッ"""
    t = t_axis(4.5)
    x = lowpass(noise(4.5), 1500) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.7 * t))
    x += sweep(500, 900, 4.5) * 0.08 * (0.5 + 0.5 * np.sin(2 * np.pi * 1.3 * t))
    return norm(x * env(len(t), 0.3, 0.8))


def freeze():
    """カチーン！と凍る"""
    t = t_axis(1.0)
    x = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in [(2637, 5), (3520, 7), (4699, 9)])
    crack = noise(1.0) * np.exp(-t * 40) * 0.8
    return norm(x * 0.6 + crack, 0.8)


def puff_up():
    """ピコの毛が逆立ってふくらむ「ボワッ」"""
    t = t_axis(0.5)
    x = sweep(150, 700, 0.5) * 0.6 + lowpass(noise(0.5), 3000) * 0.5
    return norm(x * env(len(t), 0.02, 0.15), 0.8)


def munch():
    """もぐもぐ"""
    out = []
    for i in range(4):
        t = t_axis(0.11)
        out.append(lowpass(noise(0.11), 1500) * np.sin(np.pi * t / 0.11) ** 2)
        out.append(np.zeros(int(SR * 0.07)))
    return norm(np.concatenate(out), 0.6)


def pat():
    """雪をペタペタ"""
    out = []
    for i in range(3):
        t = t_axis(0.12)
        out.append(lowpass(noise(0.12), 900) * np.exp(-t * 40))
        out.append(np.zeros(int(SR * 0.12)))
    return norm(np.concatenate(out), 0.7)


def crunch_steps():
    """雪をのしのし歩く"""
    out = []
    for i in range(4):
        t = t_axis(0.25)
        out.append(lowpass(noise(0.25), 2500) * np.exp(-t * 14))
        out.append(np.zeros(int(SR * 0.3)))
    return norm(np.concatenate(out), 0.7)


def creak():
    """ミシッ…"""
    t = t_axis(0.6)
    f = 180 + 60 * np.sin(2 * np.pi * 3 * t)
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * (0.5 + 0.5 * noise(0.6))
    return norm(lowpass(x, 1200) * env(len(t), 0.05, 0.2), 0.6)


def crumble():
    """かまくらがドサドサッと崩れる"""
    t = t_axis(1.6)
    x = lowpass(noise(1.6), 600) * np.exp(-t * 2.5)
    for k in range(6):
        s = int(SR * rng.uniform(0, 0.9))
        tt = t_axis(0.2)
        hit = np.sin(2 * np.pi * rng.uniform(60, 110) * tt) * np.exp(-tt * 18)
        x[s:s + len(hit)] += hit
    return norm(x)


# ---------------- BGM ----------------

def pluck(freq, sec, decay=0.996):
    """弦をはじく音（ピチカート風、Karplus-Strong）"""
    n = int(SR * sec)
    period = int(SR / freq)
    buf = rng.uniform(-1, 1, period)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = decay * 0.5 * (buf[i % period] + buf[(i + 1) % period])
    return out


def glock(freq, sec):
    t = t_axis(sec)
    return (np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * freq * 3.01 * t)) * np.exp(-t * 5)


def note(name):
    names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    n, octv = name[:-1], int(name[-1])
    semi = names[n[0]] + (1 if "#" in n else 0)
    return 440 * 2 ** ((semi - 9) / 12 + (octv - 4))


def bgm(total=32.0, bpm=112):
    """のんびり＆ちょっとコミカルなピチカート曲（8小節ループ×2）"""
    beat = 60 / bpm
    out = np.zeros(int(SR * (total + 2)))
    chords = [["C3", "G3"], ["A2", "E3"], ["F2", "C3"], ["G2", "D3"]]
    melody = ["E5", "G5", "E5", "C5", "D5", "-", "G4", "-",
              "C5", "E5", "A5", "G5", "E5", "-", "-", "-",
              "F5", "A5", "F5", "C5", "D5", "E5", "D5", "-",
              "G5", "F5", "E5", "D5", "C5", "-", "G4", "-"]
    step = 0
    t = 0.0
    while t < total:
        bar = int(t / (beat * 4)) % 4
        # ベース（1拍目と3拍目）
        for k, b in enumerate(chords[bar]):
            s = int(SR * (t + k * beat * 2))
            p = pluck(note(b), beat * 1.8) * 0.55
            out[s:s + len(p)] += p
        # 裏拍のコード（ポン）
        for k in range(4):
            s = int(SR * (t + k * beat + beat / 2))
            for b in chords[bar]:
                p = pluck(note(b) * 2, beat * 0.4, 0.98) * 0.18
                out[s:s + len(p)] += p
        # メロディ（8分音符）
        for k in range(8):
            m = melody[step % len(melody)]
            step += 1
            if m != "-":
                s = int(SR * (t + k * beat / 2))
                g = glock(note(m), beat * 1.5) * 0.25
                pk = pluck(note(m), beat * 0.6, 0.99) * 0.2
                g[:len(pk)] += pk
                out[s:s + len(g)] += g
        t += beat * 4
    out = out[: int(SR * total)]
    out *= env(len(out), 0.02, 1.5)
    return norm(out, 0.8)


SE = {
    "snore": snore, "small_snore": small_snore, "pop_in": pop_in, "whoosh": whoosh,
    "tada": tada, "tick": tick, "alarm": alarm, "rustle_thud": rustle_thud,
    "clang": clang, "deflate": deflate, "eye_pop": eye_pop, "slide_down": slide_down,
    "tumble": tumble, "snow_poof": snow_poof,
    "sneeze": sneeze, "shutter": shutter, "rumble": rumble, "wind": wind, "freeze": freeze,
    "puff_up": puff_up, "munch": munch, "pat": pat, "crunch_steps": crunch_steps,
    "creak": creak, "crumble": crumble,
}

if __name__ == "__main__":
    for name, fn in SE.items():
        save(os.path.join(ROOT, "assets/se", f"{name}.wav"), fn())
        print("SE ", name)
    save(os.path.join(ROOT, "assets/bgm", "snow_pizzicato.wav"), bgm())
    print("BGM snow_pizzicato")
