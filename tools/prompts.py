"""カット割り表から、画像・動画生成用のプロンプトを組み立てる。

使い方:
  python3 tools/prompts.py 001_last_berry      # storyboard/<slug>/prompts.md を作る
  python3 tools/prompts.py --sheets            # assets/characters/prompts.md（設定画用）を作る

キャラの説明文は characters.md から一字一句そのまま差し込む（ブレ防止）。
"""
from __future__ import annotations

import argparse
import json

from common import ROOT, ASSETS, load_blocks, load_storyboard

CHARACTERS = ["goro", "pipi", "don"]
SHEET_VIEWS = {
    "turnaround": "character turnaround sheet, the same character shown three times side by side: front view, side view, back view, "
                  "full body, neutral standing pose, plain white background, even studio lighting",
    "expressions": "character expression sheet, four head-and-shoulders portraits of the same character in a 2x2 grid: "
                   "overjoyed, shocked, heartbroken, desperate, plain white background",
}


def image_prompt(blocks: dict, chars: list[str], scene: str, camera: str) -> str:
    who = " ".join(f"[{c.upper()}] {blocks[c]}." for c in chars)
    return f"{blocks['style']}. {who} SCENE: {scene}. CAMERA: {camera}."


def video_prompt(blocks: dict, chars: list[str], motion: str, camera: str) -> str:
    names = ", ".join(c.capitalize() for c in chars if c in CHARACTERS)
    keep = f" Keep {names} exactly as in the start image: same colors, eye color, proportions and markings." if names else ""
    return (f"{motion}. CAMERA: {camera}. Stylized 3D animated film look, smooth cartoon motion, "
            f"exaggerated comedic timing, no text.{keep}")


def build_cuts(slug: str) -> list[dict]:
    blocks = load_blocks()
    sb = load_storyboard(slug)
    out = []
    for c in sb["cuts"]:
        out.append({
            "id": c["id"],
            "gen_seconds": c["gen_seconds"],
            "image_prompt": image_prompt(blocks, c["characters"], " ".join(c["frame"].split()), c["camera"]),
            "video_prompt": video_prompt(blocks, c["characters"], " ".join(c["motion"].split()), c["camera"]),
            "negative": blocks["negative"],
            "reference_sheets": [f"assets/characters/{ch}_turnaround.png" for ch in c["characters"] if ch in CHARACTERS],
        })
    return out


def write_cut_prompts(slug: str) -> None:
    sb = load_storyboard(slug)
    cuts = build_cuts(slug)
    d = ROOT / "storyboard" / slug
    (d / "prompts.json").write_text(json.dumps(cuts, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# {sb['title']} 生成プロンプト（自動生成・手で編集しない）\n",
             "元データ: storyboard.md と characters.md。直したいときはそちらを直して再実行。\n"]
    for c in cuts:
        lines += [f"## {c['id']}（生成 {c['gen_seconds']}秒）\n",
                  "**最初の1枚（画像）**\n", f"```\n{c['image_prompt']}\n```\n",
                  "**動画（画像→動画）**\n", f"```\n{c['video_prompt']}\n```\n",
                  "**ネガティブ**\n", f"```\n{c['negative']}\n```\n",
                  f"参照画像: {', '.join(c['reference_sheets']) or 'なし'}\n"]
    (d / "prompts.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出し: storyboard/{slug}/prompts.md, prompts.json（{len(cuts)}カット）")


def write_sheet_prompts() -> None:
    blocks = load_blocks()
    data, lines = [], ["# 設定画プロンプト（自動生成）\n"]
    for ch in CHARACTERS:
        for view, desc in SHEET_VIEWS.items():
            p = f"{blocks['style']}. {blocks[ch]}. {desc}."
            data.append({"id": f"{ch}_{view}", "image_prompt": p, "negative": blocks["negative"]})
            lines += [f"## {ch}_{view}\n", f"```\n{p}\n```\n"]
    out = ASSETS / "characters"
    (out / "prompts.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "prompts.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"書き出し: assets/characters/prompts.md, prompts.json（{len(data)}枚分）")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--sheets", action="store_true")
    a = ap.parse_args()
    if a.sheets:
        write_sheet_prompts()
    if a.slug:
        write_cut_prompts(a.slug)
    if not (a.sheets or a.slug):
        ap.print_help()
