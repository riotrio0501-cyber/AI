"""共通の読み込み処理（キャラ設定・カット割り表）。"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUTPUT = ROOT / "output"
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"  # index 0 = 日本語
W, H, FPS = 1080, 1920, 30


def load_blocks() -> dict[str, str]:
    """characters.md の ```prompt:名前 ... ``` ブロックを辞書で返す。"""
    text = (ROOT / "characters.md").read_text(encoding="utf-8")
    blocks = {}
    for name, body in re.findall(r"```prompt:(\w+)\n(.*?)```", text, re.S):
        blocks[name] = " ".join(body.split())
    return blocks


def storyboard_path(slug: str) -> Path:
    return ROOT / "storyboard" / slug / "storyboard.md"


def load_storyboard(slug: str) -> dict:
    """カット割り表の ```yaml ブロックを読み、開始時刻(start)を付けて返す。"""
    text = storyboard_path(slug).read_text(encoding="utf-8")
    m = re.search(r"```yaml\n(.*?)```", text, re.S)
    if not m:
        raise SystemExit(f"{slug}: storyboard.md に ```yaml ブロックがありません")
    sb = yaml.safe_load(m.group(1))
    t = 0.0
    for cut in sb["cuts"]:
        cut["start"] = t
        t += float(cut["duration"])
    sb["total"] = t
    return sb


def cut_by_id(sb: dict, cut_id: str) -> dict:
    for c in sb["cuts"]:
        if c["id"] == cut_id:
            return c
    raise SystemExit(f"カット {cut_id} が見つかりません")
