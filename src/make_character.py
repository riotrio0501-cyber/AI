"""character.yaml からキャラのSVGパーツを生成する。

使い方: python src/make_character.py taro   （引数なしで全キャラ）
出力: characters/<name>/parts/*.svg

キャンバスは全パーツ共通で 600x1000。重ねるだけで1体になる。
重ね順: hair_back → body → arm_l / arm_r → head → eyes → brows → mouth → hair_front
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
W, H = 600, 1000
FACES = ["normal", "surprised", "angry", "troubled", "smile"]
EYE_L, EYE_R, EYE_Y = 225, 375, 375
MOUTH_X, MOUTH_Y = 300, 462
OUTLINE = "#5B4033"  # 柔らかい焦げ茶の線


def svg(body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">{body}</svg>')


def darker(hex_color: str, k: float = 0.7) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02X%02X%02X" % (int(r * k), int(g * k), int(b * k))


def mirror(fn):
    """左目用の描画関数を、左右両方に適用する（cx と向き sx を渡す）。"""
    return fn(EYE_L, 1) + fn(EYE_R, -1)


# ---------- 目 ----------
def eyes(face: str, c: dict) -> str:
    col = c["eye"]

    def normal(cx, sx, ry=30):
        return (f'<ellipse cx="{cx}" cy="{EYE_Y}" rx="21" ry="{ry}" fill="{col}"/>'
                f'<circle cx="{cx + 6}" cy="{EYE_Y - ry * 0.35}" r="7.5" fill="#fff"/>'
                f'<circle cx="{cx - 6}" cy="{EYE_Y + ry * 0.45}" r="3.5" fill="#fff" opacity=".8"/>')

    def surprised(cx, sx):
        return (f'<circle cx="{cx}" cy="{EYE_Y}" r="30" fill="#fff" stroke="{col}" stroke-width="4.5"/>'
                f'<circle cx="{cx}" cy="{EYE_Y + 2}" r="10" fill="{col}"/>')

    def angry(cx, sx):
        # 上辺が内側に向かって下がる目
        x0, x1 = cx - 24 * sx, cx + 24 * sx
        return (f'<path d="M {x0} {EYE_Y - 18} L {x1} {EYE_Y + 2} '
                f'Q {x1} {EYE_Y + 32} {cx} {EYE_Y + 32} Q {x0} {EYE_Y + 32} {x0} {EYE_Y} Z" fill="{col}"/>'
                f'<circle cx="{cx - 4 * sx}" cy="{EYE_Y + 4}" r="5" fill="#fff"/>')

    def smile(cx, sx):
        return (f'<path d="M {cx - 26} {EYE_Y + 10} Q {cx} {EYE_Y - 26} {cx + 26} {EYE_Y + 10}" '
                f'fill="none" stroke="{col}" stroke-width="9" stroke-linecap="round"/>')

    def closed(cx, sx):
        return (f'<path d="M {cx - 26} {EYE_Y} Q {cx} {EYE_Y + 16} {cx + 26} {EYE_Y}" '
                f'fill="none" stroke="{col}" stroke-width="8" stroke-linecap="round"/>')

    table = {
        "normal": normal,
        "troubled": lambda cx, sx: normal(cx, sx, ry=25),
        "surprised": surprised,
        "angry": angry,
        "smile": smile,
        "closed": closed,
    }
    return mirror(table[face])


# ---------- 眉 ----------
def brows(face: str, c: dict, width: int) -> str:
    col = darker(c["hair"], 0.75)

    def line(d):
        return (f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{width}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')

    def shape(cx, sx):
        o, i = cx - 30 * sx, cx + 30 * sx  # 外側, 内側
        y = 312
        if face == "normal":
            return line(f"M {o} {y + 4} Q {cx} {y - 12} {i} {y + 2}")
        if face == "smile":
            return line(f"M {o} {y} Q {cx} {y - 18} {i} {y - 2}")
        if face == "surprised":
            return line(f"M {o} {y - 18} Q {cx} {y - 36} {i} {y - 20}")
        if face == "angry":
            return line(f"M {o} {y - 10} L {i} {y + 16}")
        if face == "troubled":
            return line(f"M {o} {y + 10} Q {cx} {y + 2} {i} {y - 14}")
        raise ValueError(face)

    return mirror(shape)


# ---------- 口 ----------
def mouth(face: str, level: int) -> str:
    """level: 0=閉, 1=半開き, 2=全開"""
    x, y = MOUTH_X, MOUTH_Y
    inside = "#7A2E3A"
    tongue = "#F2808A"
    st = f'fill="none" stroke="{OUTLINE}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"'
    fill = f'fill="{inside}" stroke="{OUTLINE}" stroke-width="5" stroke-linejoin="round"'

    if level == 0:
        return {
            "normal": f'<path d="M {x-18} {y-4} Q {x} {y+8} {x+18} {y-4}" {st}/>',
            "smile": f'<path d="M {x-34} {y-12} Q {x} {y+26} {x+34} {y-12}" {st}/>',
            "angry": f'<path d="M {x-22} {y+8} Q {x} {y-10} {x+22} {y+8}" {st}/>',
            "troubled": f'<path d="M {x-26} {y+2} Q {x-13} {y-10} {x} {y+2} Q {x+13} {y+14} {x+26} {y+2}" {st}/>',
            "surprised": f'<ellipse cx="{x}" cy="{y}" rx="11" ry="14" {fill}/>',
        }[face]

    if face == "smile":
        dy = 30 if level == 1 else 52
        return (f'<path d="M {x-36} {y-12} Q {x} {y+dy*1.6} {x+36} {y-12} Z" {fill}/>'
                + (f'<ellipse cx="{x}" cy="{y+dy*0.55}" rx="16" ry="{dy*0.25}" fill="{tongue}"/>' if level == 2 else ""))
    if face == "angry":
        if level == 1:
            return f'<path d="M {x-24} {y-4} L {x+24} {y-4} L {x+18} {y+16} L {x-18} {y+16} Z" {fill}/>'
        return (f'<path d="M {x-34} {y-12} L {x+34} {y-12} L {x+22} {y+40} Q {x} {y+48} {x-22} {y+40} Z" {fill}/>'
                f'<rect x="{x-28}" y="{y-10}" width="56" height="9" fill="#fff"/>')
    if face == "surprised":
        rx, ry = (15, 21) if level == 1 else (20, 30)
        return f'<ellipse cx="{x}" cy="{y+4}" rx="{rx}" ry="{ry}" {fill}/>'
    # normal / troubled
    rx, ry = (19, 12) if level == 1 else (25, 24)
    t = f'<ellipse cx="{x}" cy="{y+4+ry*0.45}" rx="{rx*0.6}" ry="{ry*0.35}" fill="{tongue}"/>' if level == 2 else ""
    return f'<ellipse cx="{x}" cy="{y+4}" rx="{rx}" ry="{ry}" {fill}/>' + t


# ---------- 髪 ----------
HEAD_CLIP = ('<defs><clipPath id="headclip"><ellipse cx="300" cy="355" rx="212" ry="200"/>'
             '</clipPath></defs>')


def face_shadow(d: str, c: dict) -> str:
    """前髪の影を顔に落とす（頭の形で切り抜く）。"""
    return (HEAD_CLIP + f'<g clip-path="url(#headclip)"><path d="{d}" transform="translate(6,18)" '
            f'fill="{darker(c["skin"], 0.88)}"/></g>')


def hair(style: str, c: dict):
    col = c["hair"]
    hi = "#FFFFFF"
    ol = f'stroke="{darker(col, 0.6)}" stroke-width="4.5" stroke-linejoin="round"'
    if style == "short":
        back = f'<ellipse cx="300" cy="320" rx="222" ry="200" fill="{col}" {ol}/>'
        bang = ("M 86 380 A 216 216 0 1 1 514 380 L 506 318 L 470 262 L 440 296 L 398 246 "
                "L 356 288 L 304 240 L 258 290 L 214 250 L 176 298 L 136 262 L 96 322 Z")
        front = (
            face_shadow(bang, c) +
            f'<path d="{bang}" fill="{col}" {ol}/>'
            # アホ毛ではなく「寝ぐせ」2本
            f'<path d="M 300 132 Q 318 70 372 78 Q 336 96 330 136 Z" fill="{col}" {ol}/>'
            f'<path d="M 250 140 Q 236 92 268 70 Q 262 104 282 136 Z" fill="{col}" {ol}/>'
            f'<path d="M 180 190 Q 240 150 300 152" fill="none" stroke="{hi}" stroke-width="10" '
            f'stroke-linecap="round" opacity=".35"/>'
        )
        return back, front
    if style == "bob":
        back = f'<path d="M 70 360 Q 60 130 300 118 Q 540 130 530 360 L 540 560 Q 300 600 60 560 Z" fill="{col}" {ol}/>'
        acc = c.get("accent", "#FFD54F")
        sx, sy = 448, 206
        import math
        pts = []
        for k in range(10):
            r = 30 if k % 2 == 0 else 13
            a = -math.pi / 2 + k * math.pi / 5
            pts.append(f"{sx + r * math.cos(a):.1f},{sy + r * math.sin(a):.1f}")
        star = f'<polygon points="{" ".join(pts)}" fill="{acc}" stroke="{darker(acc, 0.65)}" stroke-width="4" stroke-linejoin="round"/>'
        bang = ("M 78 470 Q 70 140 300 128 Q 530 140 522 470 L 492 470 Q 498 330 478 286 "
                "Q 440 262 408 276 Q 376 254 344 274 Q 312 252 280 274 Q 248 252 216 274 "
                "Q 184 256 150 280 Q 108 300 108 470 Z")
        front = (
            face_shadow(bang, c) +
            f'<path d="{bang}" fill="{col}" {ol}/>'
            f'<path d="M 170 190 Q 240 158 320 160" fill="none" stroke="{hi}" stroke-width="10" '
            f'stroke-linecap="round" opacity=".35"/>'
            + star
        )
        return back, front
    raise ValueError(style)


# ---------- 体・腕・頭 ----------
TORSO = "M 214 560 Q 300 530 386 560 Q 420 680 424 820 Q 300 846 176 820 Q 180 680 214 560 Z"


def body(c: dict) -> str:
    ol = f'stroke="{OUTLINE}" stroke-width="4.5" stroke-linejoin="round"'
    return (
        # 脚
        f'<rect x="222" y="780" width="66" height="160" rx="22" fill="{c["pants"]}" {ol}/>'
        f'<rect x="312" y="780" width="66" height="160" rx="22" fill="{c["pants"]}" {ol}/>'
        f'<ellipse cx="250" cy="950" rx="50" ry="26" fill="{c["shoes"]}" {ol}/>'
        f'<ellipse cx="350" cy="950" rx="50" ry="26" fill="{c["shoes"]}" {ol}/>'
        # 胴体
        f'<defs><clipPath id="torso"><path d="{TORSO}"/></clipPath></defs>'
        f'<path d="{TORSO}" fill="{c["shirt"]}"/>'
        f'<g clip-path="url(#torso)">'
        f'<ellipse cx="420" cy="720" rx="90" ry="200" fill="{darker(c["shirt"], 0.86)}"/>'
        f'<ellipse cx="300" cy="555" rx="120" ry="34" fill="{darker(c["shirt"], 0.82)}"/></g>'
        f'<path d="{TORSO}" fill="none" {ol}/>'
        f'<path d="M 262 548 Q 300 590 338 548" fill="{c["skin"]}" {ol}/>'
    )


ARM_PIVOT = {"arm_l": (222, 590), "arm_r": (378, 590)}


def arm(side: str, c: dict) -> str:
    px, py = ARM_PIVOT[side]
    sx = -1 if side == "arm_l" else 1
    hx, hy = px + 40 * sx, py + 190
    return (
        f'<path d="M {px} {py} L {hx} {hy - 26}" stroke="{OUTLINE}" stroke-width="55" stroke-linecap="round"/>'
        f'<path d="M {px} {py} L {hx} {hy - 26}" stroke="{c["shirt"]}" stroke-width="46" stroke-linecap="round"/>'
        f'<circle cx="{hx}" cy="{hy}" r="27" fill="{c["skin"]}" stroke="{OUTLINE}" stroke-width="4.5"/>'
    )


def head(c: dict) -> str:
    ol = f'stroke="{OUTLINE}" stroke-width="4.5"'
    return (
        f'<ellipse cx="92" cy="400" rx="30" ry="38" fill="{c["skin"]}" {ol}/>'
        f'<ellipse cx="508" cy="400" rx="30" ry="38" fill="{c["skin"]}" {ol}/>'
        f'<ellipse cx="300" cy="355" rx="212" ry="200" fill="{c["skin"]}" {ol}/>'
        f'<ellipse cx="190" cy="440" rx="32" ry="18" fill="{c["cheek"]}" opacity=".7"/>'
        f'<ellipse cx="410" cy="440" rx="32" ry="18" fill="{c["cheek"]}" opacity=".7"/>'
    )


def build(name: str):
    d = ROOT / "characters" / name
    cfg = yaml.safe_load((d / "character.yaml").read_text(encoding="utf-8"))
    c = cfg["colors"]
    parts = d / "parts"
    parts.mkdir(exist_ok=True)

    def save(fname, body_svg):
        (parts / f"{fname}.svg").write_text(svg(body_svg), encoding="utf-8")

    hb, hf = hair(cfg["hair_style"], c)
    save("hair_back", hb)
    save("hair_front", hf)
    save("body", body(c))
    save("arm_l", arm("arm_l", c))
    save("arm_r", arm("arm_r", c))
    save("head", head(c))
    for f in FACES + ["closed"]:
        save(f"eyes_{f}", eyes(f, c))
    for f in FACES:
        save(f"brows_{f}", brows(f, c, cfg.get("brow_width", 10)))
        for lv in range(3):
            save(f"mouth_{f}_{lv}", mouth(f, lv))
    print(f"{name}: {len(list(parts.glob('*.svg')))} parts -> {parts}")


if __name__ == "__main__":
    names = sys.argv[1:] or [p.parent.name for p in (ROOT / "characters").glob("*/character.yaml")]
    for n in names:
        build(n)
