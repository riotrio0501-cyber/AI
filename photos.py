#!/usr/bin/env python3
"""Wikimedia Commons から自由ライセンスの写真を探して取り込むツール。

    python photos.py search "imoni" [--n 12]          # 候補を一覧＋サムネ一覧画像を作る
    python photos.py get "File:Imoni.jpg" assets/photos/yamagata/imoni.jpg

get すると画像（長辺1280px）と、同名の .json（作者・ライセンス・出典URL）を保存する。
make_video.py はこの .json からクレジットを自動で作る。

使ってよいライセンス: CC0 / Public domain / CC BY / CC BY-SA（いずれもクレジット表記が必要なものは自動表記）
"""
from __future__ import annotations

import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

API = "https://commons.wikimedia.org/w/api.php"
UA = "PrefectureShortsVideoTool/1.0 (low-volume script)"
OK_LICENSE = re.compile(r"^(cc0|cc[- ]by(-sa)?[- ]?\d|public domain|pd)", re.I)
ROOT = Path(__file__).resolve().parent
_last = 0.0


def _get(url: str) -> bytes:
    global _last
    wait = 3.0 - (time.time() - _last)
    if wait > 0:
        time.sleep(wait)  # 3秒に1回まで（Wikimedia の回数制限対策）
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                _last = time.time()
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(30 * (attempt + 1))
                continue
            raise


def api(**params) -> dict:
    params.update(format="json")
    return json.loads(_get(API + "?" + urllib.parse.urlencode(params)))


def strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def info(titles: list[str], width=1280) -> list[dict]:
    d = api(action="query", prop="imageinfo", titles="|".join(titles),
            iiprop="url|extmetadata|size|mime", iiurlwidth=width)
    out = []
    for p in d["query"]["pages"].values():
        if "imageinfo" not in p:
            continue
        ii = p["imageinfo"][0]
        m = ii.get("extmetadata", {})
        lic = strip_html(m.get("LicenseShortName", {}).get("value", ""))
        out.append({
            "title": p["title"],
            "license": lic,
            "license_ok": bool(OK_LICENSE.match(lic)),
            "artist": strip_html(m.get("Artist", {}).get("value", "")) or "不明",
            "description": strip_html(m.get("ImageDescription", {}).get("value", ""))[:120],
            "page": ii.get("descriptionurl"),
            "thumb": ii.get("thumburl") or ii.get("url"),
            "orig": ii.get("url"),  # upload.wikimedia.org の元画像
            "size": (ii.get("width"), ii.get("height")),
            "mime": ii.get("mime"),
        })
    return out


def search(q: str, n=12) -> list[dict]:
    d = api(action="query", list="search", srsearch=f"{q} filetype:bitmap", srnamespace=6, srlimit=n)
    titles = [s["title"] for s in d["query"]["search"]]
    return info(titles, width=400) if titles else []


def contact_sheet(items: list[dict], path: Path):
    font = ImageFont.truetype(str(ROOT / "assets/fonts/MPLUSRounded1c-ExtraBold.ttf"), 16)
    W, H, cols = 320, 260, 4
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGB", (W * cols, H * rows), "white")
    d = ImageDraw.Draw(sheet)
    for i, it in enumerate(items):
        x, y = (i % cols) * W, (i // cols) * H
        try:
            im = Image.open(io.BytesIO(_get(it["thumb"]))).convert("RGB")
            im.thumbnail((W - 10, H - 50))
            sheet.paste(im, (x + 5, y + 5))
        except Exception as e:  # noqa
            d.text((x + 5, y + 5), f"load error {e}", fill="red", font=font)
        mark = "OK" if it["license_ok"] else "NG"
        d.text((x + 5, y + H - 44), f"[{i}] {mark} {it['license']}", fill="black", font=font)
        d.text((x + 5, y + H - 24), it["title"][5:40], fill="gray", font=font)
    sheet.save(path)


def get(title: str, out: Path):
    it = info([title], width=1280)[0]
    if it["size"][0] and it["size"][0] <= 1280:
        # 元画像が小さいとサムネイルが作られず元画像URLになる（=回数制限に掛かる）。
        # Wikimedia が受け付ける標準サイズのうち、元画像より小さい最大の幅で取り直す
        std = [w for w in (120, 250, 330, 500, 960) if w < it["size"][0]]
        it = info([title], width=std[-1])[0]
    if not it["license_ok"]:
        sys.exit(f"ライセンスが使えない可能性: {it['license']} ({title})")
    # Wikimedia の方針に沿ってサムネイル（thumb.wikimedia.org 配信, 幅1280）を取得する
    im = Image.open(io.BytesIO(_get(it["thumb"]))).convert("RGB")
    im.thumbnail((1280, 1280), Image.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, quality=92)
    meta = {k: it[k] for k in ("title", "license", "artist", "page")}
    meta["credit"] = f"写真: {it['artist']} / {it['license']} / Wikimedia Commons"
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"saved {out}  ({im.size[0]}x{im.size[1]})  {meta['credit']}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "search":
        n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 12
        items = search(sys.argv[2], n)
        for i, it in enumerate(items):
            print(f"[{i}] {'OK' if it['license_ok'] else 'NG'} {it['license']:14s} {it['size']} {it['title']}  | {it['description'][:60]}")
        if "--sheet" in sys.argv:  # サムネ一覧画像（リクエストが増えるので必要なときだけ）
            sheet = Path(sys.argv[sys.argv.index("--sheet") + 1])
            contact_sheet(items, sheet)
            print("sheet:", sheet)
    elif len(sys.argv) == 4 and sys.argv[1] == "get":
        get(sys.argv[2], Path(sys.argv[3]))
    else:
        print(__doc__)
