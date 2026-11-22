#!/usr/bin/env python3
"""Gonta & Piko エピソード制作ツール

  python3 tools/episode.py plan  episodes/01_haru_okinai   # 生成用プロンプトと必要クレジットを表示・保存
  python3 tools/episode.py build episodes/01_haru_okinai   # 素材をつないで完成動画を作る

素材（frames/*.png, clips/*.mp4）がまだ無いカットは「仮の絵」で埋めるので、
いつでも全体の流れ（尺・テロップ・効果音・BGM）を確認できる。
"""
import json
import math
import os
import subprocess
import sys
import wave
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS, SR = 1080, 1920, 30, 44100
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

# クレジット単価（Higgsfield）
COST_VIDEO_PER_SEC = 2      # minimax_h3
COST_IMAGE = 3              # minimax_h3_image 1k


def load(ep_dir):
    with open(os.path.join(ep_dir, "storyboard.json"), encoding="utf-8") as f:
        sb = json.load(f)
    with open(os.path.join(ROOT, "characters/prompts.json"), encoding="utf-8") as f:
        ch = json.load(f)
    return sb, ch


def run(cmd, **kw):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, **kw)


# ------------------------------------------------------------------ plan

def build_prompt(cut, ch):
    who = " ".join(ch[c] + "." for c in cut["chars"])
    return f"{cut['action']}. {who} {ch['style']}. Avoid: {ch['negative']}."


def plan(ep_dir):
    sb, ch = load(ep_dir)
    items, total, seen = [], 0, set()
    for cut in sb["cuts"]:
        if cut["src"] in seen:          # 同じ絵の使い回し（ループ用など）はお金がかからない
            continue
        seen.add(cut["src"])
        refs = [ch["reference_images"].get(c) for c in cut["chars"]]
        if cut["type"] == "video":
            cost = COST_VIDEO_PER_SEC * cut["dur"]
            item = {"cut": cut["id"], "model": "minimax_h3", "duration": cut["dur"],
                    "aspect_ratio": "9:16", "save_as": cut["src"]}
        else:
            cost = COST_IMAGE
            item = {"cut": cut["id"], "model": "minimax_h3_image", "resolution": "1k",
                    "aspect_ratio": "9:16", "save_as": cut["src"]}
        item.update(prompt=build_prompt(cut, ch), reference_job_ids=refs, credits=cost,
                    done=os.path.exists(os.path.join(ep_dir, cut["src"])))
        items.append(item)
        total += cost
    todo = sum(i["credits"] for i in items if not i["done"])
    out = {"episode": sb["id"], "total_credits": total, "remaining_credits": todo, "items": items}
    with open(os.path.join(ep_dir, "generation_plan.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    write_md(ep_dir, sb, total)
    for i in items:
        mark = "済" if i["done"] else "未"
        print(f"[{mark}] カット{i['cut']}: {i['model']:16s} {i['credits']:>3} クレジット")
    print(f"合計 {total} クレジット（未生成ぶん {todo}）")
    if any(r is None for i in items for r in i["reference_job_ids"]):
        print("※ キャラの参照画像がまだ決まっていません（characters/prompts.json）")


MOTION_JA = {"static": "動かない", "slow_push": "ゆっくり寄る", "zoom_in": "寄る", "zoom_out": "引く",
             "punch_zoom": "ドンッと寄る", "shake": "揺れる"}


def write_md(ep_dir, sb, total):
    """storyboard.json から人が読む用のカット割り表を作る"""
    srcs, rows, sec = {}, [], 0
    for c in sb["cuts"]:
        how = "動画" if c["type"] == "video" else "静止画＋" + MOTION_JA.get(c.get("motion", "static"), "")
        if c["src"] in srcs:
            how += f"（カット{srcs[c['src']]}の絵を使い回し）"
        srcs.setdefault(c["src"], c["id"])
        tel = c.get("telop")
        desc = c.get("desc", c["action"][:60])
        if tel:
            desc += f"<br>テロップ「{tel['text']}／{tel.get('sub', '')}」"
        se = "・".join(x["name"] for x in c.get("se", []))
        if "bgm_stop" in c:
            se = "BGM止まる・" + se
        rows.append(f"| {c['id']} | {c['dur']} | {desc} | {how} | {se} |")
        sec += c["dur"]
    md = [f"# {sb['id'][:2]}「{sb['title_ja']}」/ {sb['title_en']}（{sec}秒）", ""]
    if sb.get("note"):
        md += [sb["note"], ""]
    md += ["中身の正本は `storyboard.json`（ここは自動で作られる表。直接書きかえない）", "",
           "| # | 秒 | 内容 | 作り方 | 効果音 |", "|---|---|---|---|---|"] + rows
    md += ["", f"クレジット：**{total}**"]
    with open(os.path.join(ep_dir, "storyboard.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")


# ------------------------------------------------------------------ 映像

def cover(img, w, h):
    s = max(w / img.width, h / img.height)
    img = img.resize((math.ceil(img.width * s), math.ceil(img.height * s)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def ease_out(x):
    return 1 - (1 - min(max(x, 0), 1)) ** 3


def motion_params(kind, t, dur):
    """(zoom, dx, dy) を返す。zoom>=1。"""
    p = t / dur
    if kind == "slow_push":
        return 1.0 + 0.08 * p, 0, 0
    if kind == "zoom_out":     # 寄りから引いて全体を見せる（オチの種明かし）
        return 1.2 - 0.2 * ease_out(p), 0, 0
    if kind == "zoom_in":
        return 1.0 + 0.2 * ease_out(p), 0, 0
    if kind == "punch_zoom":   # ドンッと寄ってから、ゆっくり
        return 1.0 + 0.25 * (1 - ease_out(t / 0.25)) + 0.05 * p, 0, 0
    if kind == "shake":        # ヘトヘトでフラフラ
        amp = 16
        return 1.06, amp * math.sin(t * 2 * math.pi * 2.3) + 6 * math.sin(t * 31), \
            amp * 0.6 * math.sin(t * 2 * math.pi * 1.7 + 1) + 6 * math.cos(t * 27)
    return 1.0, 0, 0


def placeholder(cut, path):
    colors = {"video": (60, 90, 140), "image": (80, 120, 90)}
    img = Image.new("RGB", (W, H), colors[cut["type"]])
    d = ImageDraw.Draw(img)
    f1, f2 = ImageFont.truetype(FONT_BOLD, 110), ImageFont.truetype(FONT_REG, 40)
    d.text((W / 2, 500), f"CUT {cut['id']}", font=f1, fill="white", anchor="mm")
    d.text((W / 2, 640), f"{cut['type']} / {cut['dur']}s / 仮の絵", font=f2, fill="white", anchor="mm")
    words, line, y = cut["action"].split(), "", 760
    for wd in words:
        if len(line) + len(wd) > 38:
            d.text((80, y), line, font=f2, fill=(230, 230, 230)); y += 56; line = ""
        line += wd + " "
    d.text((80, y), line, font=f2, fill=(230, 230, 230))
    img.save(path)


def render_still(src, motion, dur, out):
    base = cover(Image.open(src).convert("RGB"), int(W * 1.3), int(H * 1.3))
    n = int(round(dur * FPS))
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                          "-crf", "18", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    bw, bh = base.size
    for i in range(n):
        z, dx, dy = motion_params(motion, i / FPS, dur)
        # 高解像度(1.3倍)の元画像から、ズーム量に合わせた範囲を切り出す（z=1で全体）
        k = bw / W
        cw, ch_ = bw / z, bh / z
        cx = min(max(bw / 2 - dx * k / z, cw / 2), bw - cw / 2)
        cy = min(max(bh / 2 - dy * k / z, ch_ / 2), bh - ch_ / 2)
        a = cw / W
        frame = base.transform((W, H), Image.AFFINE, (a, 0, cx - cw / 2, 0, a, cy - ch_ / 2), Image.BICUBIC)
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    p.wait()


def render_video(src, dur, out):
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},"
          f"tpad=stop_mode=clone:stop_duration={dur},trim=duration={dur},setpts=PTS-STARTPTS")
    run(["ffmpeg", "-y", "-i", src, "-an", "-vf", vf, "-c:v", "libx264", "-preset", "medium",
         "-crf", "18", "-pix_fmt", "yuv420p", out])


def telop_png(tel, path):
    """大きい日本語＋小さい英語。白文字＋太いフチ＋ふんわり影"""
    img = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
    big = ImageFont.truetype(FONT_BOLD, 104)
    small = ImageFont.truetype(FONT_BOLD, 50)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    d = ImageDraw.Draw(img)
    rows = [(tel["text"], big, 150, 14)]
    if tel.get("sub"):
        rows.append((tel["sub"], small, 290, 8))
    for text, font, y, stroke in rows:
        sd.text((W / 2 + 6, y + 10), text, font=font, fill=(0, 0, 0, 150), anchor="mm",
                stroke_width=stroke, stroke_fill=(0, 0, 0, 150))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    for text, font, y, stroke in rows:
        d.text((W / 2, y), text, font=font, fill=(255, 255, 255), anchor="mm",
               stroke_width=stroke, stroke_fill=(150, 28, 28))
    Image.alpha_composite(shadow, img).save(path)


# ------------------------------------------------------------------ 音

def read_wav(path):
    with wave.open(path) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return x.reshape(-1, w.getnchannels()).mean(axis=1) if w.getnchannels() > 1 else x


def mix_audio(sb, starts, total, out):
    mix = np.zeros(int(SR * total) + SR)
    bgm = sb.get("bgm")
    if bgm:
        b = read_wav(os.path.join(ROOT, bgm["file"])) * bgm.get("volume", 0.3)
        end = total
        for cut, st in zip(sb["cuts"], starts):
            if "bgm_stop" in cut:      # オチ前でBGMをピタッと止める（静けさで笑わせる）
                end = st + cut["bgm_stop"]
        b = np.tile(b, int(end * SR // len(b)) + 1)[: int(end * SR)]
        fade = min(len(b), int(SR * 0.08))
        b[-fade:] *= np.linspace(1, 0, fade)
        mix[: len(b)] += b
    for cut, st in zip(sb["cuts"], starts):
        for se in cut.get("se", []):
            x = read_wav(os.path.join(ROOT, "assets/se", se["name"] + ".wav")) * se.get("vol", 0.8)
            s = int(SR * (st + se["at"]))
            x = x[: max(0, len(mix) - s)]
            mix[s: s + len(x)] += x
    mix = mix[: int(SR * total)]
    peak = np.max(np.abs(mix)) or 1
    if peak > 0.95:
        mix *= 0.95 / peak
    data = (mix * 32767).astype(np.int16)
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())


# ------------------------------------------------------------------ build

def build(ep_dir):
    sb, _ = load(ep_dir)
    work = os.path.join(ep_dir, "build")
    os.makedirs(work, exist_ok=True)
    segs, starts, t, missing, jobs = [], [], 0.0, [], []
    first_use = {}
    for cut in sb["cuts"]:
        first_use.setdefault(cut["src"], cut["id"])
    for cut in sb["cuts"]:
        src = os.path.join(ep_dir, cut["src"])
        seg = os.path.join(work, f"seg{cut['id']:02d}.mp4")
        if not os.path.exists(src):
            missing.append(cut["id"])
            src = os.path.join(work, "ph_" + cut["src"].replace("/", "_") + ".png")
            if not os.path.exists(src) or cut["id"] == first_use[cut["src"]]:
                placeholder(cut, src)   # 使い回しのカットは、最初のカットの仮の絵をそのまま使う
            jobs.append((render_still, src, cut.get("motion", "slow_push"), cut["dur"], seg))
        elif cut["type"] == "video":
            jobs.append((render_video, src, cut["dur"], seg))
        else:
            jobs.append((render_still, src, cut.get("motion", "static"), cut["dur"], seg))
        segs.append(seg); starts.append(t); t += cut["dur"]
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:   # カットを同時に作って時短
        for f in [ex.submit(j[0], *j[1:]) for j in jobs]:
            f.result()
    print("カットの書き出し OK" + (f"（仮の絵: {missing}）" if missing else ""))
    total = t

    lst = os.path.join(work, "concat.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{os.path.abspath(s)}'\n" for s in segs)
    joined = os.path.join(work, "joined.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])

    # テロップ
    inputs, filters, last = ["-i", joined], [], "0:v"
    n = 1
    for cut, st in zip(sb["cuts"], starts):
        tel = cut.get("telop")
        if not tel:
            continue
        png = os.path.join(work, f"telop{cut['id']:02d}.png")
        telop_png(tel, png)
        a, b = st + tel["start"], st + tel["end"]
        inputs += ["-loop", "1", "-t", f"{total}", "-i", png]
        filters.append(f"[{n}:v]format=rgba,fade=in:st={a}:d=0.2:alpha=1,fade=out:st={b - 0.2}:d=0.2:alpha=1[t{n}]")
        filters.append(f"[{last}][t{n}]overlay=0:{int(H * 0.11)}:shortest=1[v{n}]")
        last = f"v{n}"; n += 1

    wav = os.path.join(work, "audio.wav")
    mix_audio(sb, starts, total, wav)

    os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)
    # 仮の絵が残っているときは「_preview」付きで保存（確認用なので git には入れない）
    out = os.path.join(ROOT, "output", f"{sb['id']}{'_preview' if missing else ''}.mp4")
    cmd = ["ffmpeg", "-y"] + inputs + ["-i", wav]
    if filters:
        cmd += ["-filter_complex", ";".join(filters), "-map", f"[{last}]"]
    else:
        cmd += ["-map", "0:v"]
    cmd += ["-map", f"{n}:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-t", f"{total}", "-movflags", "+faststart", out]
    run(cmd)

    with open(os.path.join(ROOT, "output", f"{sb['id']}_credits.txt"), "w", encoding="utf-8") as f:
        f.write(f"{sb['title_ja']} / {sb['title_en']}\n\n"
                "映像：AI生成（Higgsfield / MiniMax H3）\n"
                "効果音・BGM：オリジナル（自作）\n"
                "#GontaAndPiko #shorts #animation #funnyanimals\n")
    print(f"\n完成: {out}（{total:.0f}秒）")
    if missing:
        print(f"※ 仮の絵のカット: {missing}")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("plan", "build"):
        print(__doc__); sys.exit(1)
    {"plan": plan, "build": build}[sys.argv[1]](sys.argv[2])
