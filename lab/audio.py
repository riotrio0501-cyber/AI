"""BGM・効果音の自作（すべてコードで生成するので著作権フリー）"""
import wave

import numpy as np

from .tts import SR


def db(g):
    return 10 ** (g / 20)


def _env(n, a=0.01, r=0.3):
    t = np.arange(n) / SR
    e = np.minimum(1, t / a) * np.exp(-t / r)
    return e.astype(np.float32)


def _note(f):
    return 440.0 * 2 ** ((f - 69) / 12)


def bgm(duration, seed=0, bpm=104):
    """明るめのローファイ風ループ: パッド + プラック + キック/ハット"""
    rng = np.random.default_rng(seed)
    n = int(duration * SR)
    out = np.zeros(n, np.float32)
    beat = 60 / bpm
    # I - V - vi - IV（Cメジャー）を少しずらして毎回変える
    roots = [60, 67, 69, 65]
    shift = int(rng.integers(-2, 3))
    chords = [[r + shift, r + 4 + shift - (1 if r == 69 else 0), r + 7 + shift] for r in roots]
    bar = beat * 4
    t_all = np.arange(n) / SR
    for i in range(int(duration / bar) + 1):
        ch = chords[i % 4]
        s = int(i * bar * SR)
        e = min(n, int((i + 1) * bar * SR) + int(0.3 * SR))
        if s >= n:
            break
        t = t_all[s:e] - i * bar
        pad = sum(np.sin(2 * np.pi * _note(m - 12) * t) + 0.3 * np.sin(2 * np.pi * _note(m) * t * 1.003) for m in ch)
        fade = np.minimum(1, t / 0.4) * np.minimum(1, (bar + 0.3 - t) / 0.4).clip(0)
        out[s:e] += (0.05 * pad * fade).astype(np.float32)
        # プラック（8分のアルペジオ）
        for k in range(8):
            if rng.random() < 0.25:
                continue
            m = ch[[0, 1, 2, 1, 2, 0, 1, 2][k]] + 12
            ps = s + int(k * beat / 2 * SR)
            ln = int(0.35 * SR)
            if ps + ln > n:
                continue
            tt = np.arange(ln) / SR
            tone = np.sin(2 * np.pi * _note(m) * tt) + 0.4 * np.sin(4 * np.pi * _note(m) * tt)
            out[ps:ps + ln] += 0.06 * tone * _env(ln, 0.003, 0.12)
        # キック・ハット
        for k in range(4):
            ks = s + int(k * beat * SR)
            ln = int(0.25 * SR)
            if ks + ln > n:
                continue
            tt = np.arange(ln) / SR
            f = 50 + 70 * np.exp(-tt / 0.03)
            out[ks:ks + ln] += 0.22 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(ln, 0.002, 0.08)
            hs = ks + int(beat / 2 * SR)
            hl = int(0.05 * SR)
            if hs + hl < n:
                out[hs:hs + hl] += 0.025 * rng.standard_normal(hl).astype(np.float32) * _env(hl, 0.001, 0.015)
    # ふわっと開始・終了
    f = int(1.0 * SR)
    out[:f] *= np.linspace(0, 1, f)
    out[-f:] *= np.linspace(1, 0, f)
    return out / (np.max(np.abs(out)) or 1)


def pop():
    """シーン切り替えの「ポン」"""
    ln = int(0.12 * SR)
    t = np.arange(ln) / SR
    f = 600 + 900 * np.exp(-t / 0.02)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(ln, 0.001, 0.04)).astype(np.float32)


def whoosh():
    ln = int(0.3 * SR)
    rng = np.random.default_rng(1)
    x = rng.standard_normal(ln).astype(np.float32)
    x = np.convolve(x, np.ones(30) / 30, mode="same")
    e = np.sin(np.linspace(0, np.pi, ln)) ** 2
    return (x * e * 3).astype(np.float32)


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
