"""カット割り表どおりに、クリップ・効果音・BGM・テロップをつないで完成動画を作る。

使い方:
  python3 tools/assemble.py 001_last_berry            # output/001_last_berry.mp4
  python3 tools/assemble.py 001_last_berry --name v2  # output/001_last_berry_v2.mp4

各カットの映像は、次の順で探す（あるものを使う）:
  1. assets/clips/<slug>/<カットID>.mp4   … 動画生成AIで作ったクリップ（採用版）
  2. assets/frames/<slug>/<カットID>.png  … 最初の1枚（静止画をゆっくりズームして仮表示）
  3. どちらもなければ、カットの説明を書いた「仮カード」を自動で作る（＝絵コンテ動画）

効果音・BGMは assets/sound_credits.yaml に登録されたものだけ使える（未登録だと止まる）。
クレジット一覧を output/<名前>_credits.txt に書き出す。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import textwrap
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

from common import ASSETS, FONT, FPS, H, OUTPUT, W, load_storyboard

VCODEC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS)]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(" ".join(map(str, cmd)))
        print(r.stderr[-3000:])
        raise SystemExit("ffmpeg でエラーが出ました")


def font(size):
    return ImageFont.truetype(FONT, size, index=0)


def placeholder_card(cut: dict, title: str, path: Path):
    """生成前の「仮カード」画像。"""
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):  # 氷っぽいグラデーション
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(20 + 40 * k), int(50 + 70 * k), int(90 + 90 * k)))
    d.text((W // 2, 1640), title, font=font(40), fill=(220, 235, 255), anchor="mm")
    d.text((W // 2, 560), cut["id"].upper(), font=font(180), fill=(255, 255, 255), anchor="mm")
    d.text((W // 2, 720), f"{cut['duration']} 秒", font=font(60), fill=(180, 220, 255), anchor="mm")
    body = "\n".join(textwrap.wrap(cut["action_ja"], 14))
    d.multiline_text((W // 2, 1080), body, font=font(64), fill=(255, 255, 255), anchor="mm", align="center", spacing=24)
    d.text((W // 2, 1450), f"カメラ: {cut['camera_ja']}", font=font(44), fill=(200, 225, 255), anchor="mm")
    d.text((W // 2, 1780), "※ 仮映像（絵コンテ）", font=font(40), fill=(255, 210, 120), anchor="mm")
    img.save(path)


def telop_png(text: str, position: str, path: Path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = {"top": 330, "center": H // 2, "bottom": H - 420}[position]
    d.multiline_text((W // 2, y), text, font=font(84), fill=(255, 255, 255), anchor="mm", align="center",
                     spacing=18, stroke_width=10, stroke_fill=(20, 40, 80))
    img.save(path)


FIT = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}"


def render_cut(cut: dict, slug: str, title: str, work: Path) -> tuple[Path, str]:
    dur = float(cut["duration"])
    out = work / f"{cut['id']}.mp4"
    clip = ASSETS / "clips" / slug / f"{cut['id']}.mp4"
    frame = ASSETS / "frames" / slug / f"{cut['id']}.png"
    if clip.exists():
        src = "クリップ"
        ss = float(cut.get("trim_start", 0))
        speed = float(cut.get("speed", 1.0))
        vf = f"{FIT},setpts=PTS/{speed}" if speed != 1.0 else FIT
        run(["ffmpeg", "-y", "-ss", str(ss), "-i", clip, "-an", "-vf", vf, "-t", str(dur), *VCODEC, out])
        got = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                                   capture_output=True, text=True).stdout or 0)
        if got < dur - 0.05:  # クリップが短いときは最後のコマで延長
            ext = work / f"{cut['id']}_ext.mp4"
            run(["ffmpeg", "-y", "-i", out, "-vf", f"tpad=stop_mode=clone:stop_duration={dur - got:.3f}", *VCODEC, ext])
            ext.replace(out)
    else:
        if frame.exists():
            src, img = "静止画", frame
        else:
            src, img = "仮カード", work / f"{cut['id']}_card.png"
            placeholder_card(cut, title, img)
        n = int(dur * FPS)
        zoom = f"zoompan=z='1+0.06*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={W}x{H}:fps={FPS}"
        run(["ffmpeg", "-y", "-loop", "1", "-i", img, "-vf",
             f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{zoom}", "-t", str(dur), *VCODEC, out])
    return out, src


def build(slug: str, name: str | None):
    sb = load_storyboard(slug)
    credits_db = yaml.safe_load((ASSETS / "sound_credits.yaml").read_text(encoding="utf-8")) or {}
    work = OUTPUT / ".work" / slug
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    total = sb["total"]

    # 1) 各カットを同じ形式に揃えて書き出し
    print(f"■ {sb['title']}（{total:.1f}秒, {len(sb['cuts'])}カット）")
    segs = []
    for c in sb["cuts"]:
        seg, src = render_cut(c, slug, sb["title"], work)
        segs.append(seg)
        print(f"  {c['id']}  {c['start']:5.1f}s〜{c['start'] + c['duration']:5.1f}s  [{src}] {c['action_ja']}")
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{s.name}'\n" for s in segs))
    video = work / "video.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", video])

    # 2) 音（効果音を所定の時刻に置く＋BGM）
    used, inputs, filters, labels = [], ["-i", video], [], []
    idx = 1
    bgm = sb.get("bgm")
    if bgm:
        stop = total
        if bgm.get("stop_at_cut"):
            stop = next(c["start"] for c in sb["cuts"] if c["id"] == bgm["stop_at_cut"])
        fade = float(bgm.get("fade_out", 0.5))
        used.append(bgm["file"])
        inputs += ["-stream_loop", "-1", "-i", ASSETS / bgm["file"]]
        filters.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{stop},"
                       f"afade=t=out:st={max(0, stop - fade)}:d={fade},volume={bgm.get('volume', 0.3)}[a{idx}]")
        labels.append(f"[a{idx}]")
        idx += 1
    for c in sb["cuts"]:
        for se in c.get("se", []):
            used.append(se["file"])
            ms = int((c["start"] + float(se["at"])) * 1000)
            inputs += ["-i", ASSETS / se["file"]]
            filters.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={se.get('volume', 1)},"
                           f"adelay={ms}|{ms}[a{idx}]")
            labels.append(f"[a{idx}]")
            idx += 1
    missing = sorted({u for u in used if u not in credits_db})
    if missing:
        raise SystemExit("クレジット未登録の音素材があります（assets/sound_credits.yaml に追加してください）:\n  "
                         + "\n  ".join(missing))
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest,"
                   f"atrim=0:{total},alimiter=limit=0.95,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")

    # 3) テロップ（画像を重ねる）
    vlabel = "0:v"
    for i, tl in enumerate(sb.get("telops", [])):
        png = work / f"telop{i}.png"
        telop_png(tl["text"], tl.get("position", "top"), png)
        inputs += ["-i", png]
        filters.append(f"[{vlabel}][{idx}:v]overlay=0:0:enable='between(t,{tl['start']},{tl['end']})'[v{i}]")
        vlabel = f"v{i}"
        idx += 1

    out_name = f"{slug}_{name}" if name else slug
    out = OUTPUT / f"{out_name}.mp4"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", f"[{vlabel}]" if vlabel != "0:v" else "0:v",
         "-map", "[aout]", *VCODEC, "-c:a", "aac", "-b:a", "192k", "-t", str(total), "-movflags", "+faststart", out])

    # 4) クレジット一覧
    lines = [f"{sb['title']} 使用素材クレジット", ""]
    need = []
    for f in sorted(set(used)):
        e = credits_db[f]
        lines.append(f"- {f}: {e['title']} / {e['author']} / {e['source']} / {e['license']}"
                     f" / 商用:{'OK' if e['commercial_use'] else 'NG'} / 表記:{'必要' if e['credit_required'] else '不要'}")
        if e["credit_required"]:
            need.append(e.get("credit_text", f"{e['title']} by {e['author']}"))
        if not e["commercial_use"]:
            raise SystemExit(f"{f} は商用利用NGです。差し替えてください")
    lines += ["", "【動画の説明欄に書くクレジット】", *(need or ["（表記が必要な素材はありません）"])]
    (OUTPUT / f"{out_name}_credits.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"完成: {out.relative_to(OUTPUT.parent)}  /  クレジット: output/{out_name}_credits.txt")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--name", help="出力ファイル名の後ろに付ける名前（例: v2）")
    a = ap.parse_args()
    build(a.slug, a.name)
