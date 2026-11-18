#!/usr/bin/env python3
"""知らなきゃ損ラボ 動画書き出しコマンド

使い方:
  python make_videos.py scripts/001_juminzei_2nenme.yaml   # 1本だけ
  python make_videos.py --batch                              # 承認済み(approved)の未書き出し分を7本まとめて
  python make_videos.py --batch --count 7 --include-draft    # 下書きも含める
  python make_videos.py --check                              # 全台本のルールチェックだけ
  python make_videos.py FILE --preview                       # 静止画プレビューだけ（速い）
"""
import argparse
import sys
import time
from pathlib import Path

from lab import config, render
from lab.script import load

SCRIPTS = config.ROOT / "scripts"
OUT = config.ROOT / "out"


def report(s):
    mark = "NG" if s.errors else ("!" if s.warnings else "OK")
    print(f"[{mark}] {s.path.name}  {s.title}  ({s.length} / {', '.join(s.targets)} / {s.status})")
    for e in s.errors:
        print(f"    エラー: {e}")
    for w in s.warnings:
        print(f"    警告: {w}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--batch", action="store_true", help="scripts/ からまとめて書き出す")
    ap.add_argument("--count", type=int, default=7)
    ap.add_argument("--include-draft", action="store_true")
    ap.add_argument("--force", action="store_true", help="書き出し済みでも作り直す")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--tts", choices=["auto", "voicevox", "openjtalk"])
    a = ap.parse_args()
    if a.tts:
        config.TTS_BACKEND = a.tts

    paths = [Path(f) for f in a.files] or sorted(SCRIPTS.glob("*.y*ml"))
    scripts = [load(p) for p in paths]
    if a.check:
        for s in scripts:
            report(s)
        return
    if a.batch or not a.files:
        targets = [s for s in scripts if (s.status == "approved" or a.include_draft) and not s.errors
                   and (a.force or not (OUT / s.slug / f"{s.slug}.mp4").exists())][: a.count]
    else:
        targets = scripts
    if not targets:
        print("書き出す台本がありません（status: approved にするか --include-draft を付けてください）")
        return
    ok = 0
    for s in targets:
        report(s)
        if s.errors:
            continue
        if s.status != "approved":
            print("    ※ 下書き(draft)のまま書き出しています")
        t0 = time.time()
        mp4, dur = render.render(s, OUT / s.slug, preview_only=a.preview)
        rule = config.LENGTH_RULES[s.length]
        if not rule["min"] <= dur <= rule["max"]:
            print(f"    警告: 長さ {dur:.1f}秒 が {s.length} の範囲（{rule['min']}〜{rule['max']}秒）外")
        print(f"    → {OUT / s.slug}  ({dur:.1f}秒, 処理{time.time() - t0:.0f}秒)")
        ok += 1
    print(f"完了: {ok}/{len(targets)} 本")
    sys.exit(0 if ok == len(targets) else 1)


if __name__ == "__main__":
    main()
