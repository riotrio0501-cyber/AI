"""図解・イラスト（すべてコードで描画するので著作権フリー）

台本のシーンに `visual:` を書くと、テロップの下に表示される。

  visual: {type: icon, name: calendar, text: 6月}
  visual: {type: icons, items: [{name: coin, text: "500", label: 1つ目}, ...], caption: "5つで2,500円"}
  visual: {type: bar, items: [{label: 1年目, value: 0, text: ほぼ0円}, {label: 2年目, value: 1, text: 月1万円, highlight: true}]}
  visual: {type: compare, before: 103万円, after: 160万円, before_label: これまで, after_label: 2025年分から}
  visual: {type: months, highlight: [6,7,8,9,10,11,12], caption: 6月から天引き}
  visual: {type: steps, items: [明細を見る, サブスク一覧を開く, 使ってないものを解約]}

icon の name: calendar / coin / document / phone / student / worker / family / building /
              warning / check / cross / wallet / gift / pension / chat
"""
import math

from PIL import Image, ImageDraw, ImageFilter

from . import config
from .config import GOLD, GREEN, NAVY, W, WHITE

SS = 2  # アンチエイリアス用の拡大率
SKIN = (246, 208, 170)
HAIR = (58, 44, 40)
CORAL = (234, 104, 92)
GRAY = (200, 208, 220)
DARK = (10, 26, 50)
AREA_H = 560  # 図解エリアの高さ


def avatar(size, ring=GREEN, ring_w=0.06):
    """プロフィール画像を丸く切り抜く（無ければ「損」マーク）"""
    from PIL import ImageOps
    s = size * SS
    out = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.ellipse([0, 0, s - 1, s - 1], fill=ring)
    inner = int(s * (1 - ring_w * 2))
    off = (s - inner) // 2
    mask = Image.new("L", (inner, inner), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, inner - 1, inner - 1], fill=255)
    if config.PROFILE_IMAGE.exists():
        src = Image.open(config.PROFILE_IMAGE).convert("RGBA")
        m = int(min(src.size) * 0.1)  # 余白を少し切って中央を大きく
        src = src.crop((m, m, src.width - m, src.height - m))
        img = ImageOps.fit(src, (inner, inner), Image.LANCZOS)
    else:
        img = Image.new("RGBA", (inner, inner), NAVY + (255,))
        ImageDraw.Draw(img).text((inner / 2, inner / 2), "損", font=_font(int(inner * .5)), fill=GOLD, anchor="mm")
    out.paste(img, (off, off), mask)
    return _done(out)


def _font(size):
    from .render import font
    return font(size)


def _canvas(w, h):
    im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def _done(im):
    return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)


def _shadow(im, off=10, blur=12, alpha=110):
    """影を付けて返す（少し大きいキャンバスになる）"""
    pad = blur * 2 + off
    out = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    sh.putalpha(im.getchannel("A").point(lambda a: a * alpha // 255))
    out.alpha_composite(sh, (pad + off // 2, pad + off))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(im, (pad, pad))
    return out


def _person(d, cx, top, s, body=GREEN, cap=False, tie=False, hair=True):
    """シンプルな人物（頭＋上半身）。s=頭の半径"""
    r = s
    # 体
    d.rounded_rectangle([cx - r * 1.7, top + r * 2.1, cx + r * 1.7, top + r * 4.6], radius=int(r * 1.2), fill=body)
    if tie:
        d.polygon([(cx - r * 0.45, top + r * 2.1), (cx + r * 0.45, top + r * 2.1), (cx, top + r * 2.7)], fill=WHITE)
        d.polygon([(cx - r * 0.18, top + r * 2.45), (cx + r * 0.18, top + r * 2.45), (cx + r * 0.28, top + r * 3.7),
                   (cx, top + r * 4.0), (cx - r * 0.28, top + r * 3.7)], fill=GOLD)
    # 頭
    d.ellipse([cx - r, top, cx + r, top + r * 2], fill=SKIN)
    if hair:
        d.chord([cx - r * 1.05, top - r * 0.08, cx + r * 1.05, top + r * 1.5], 180, 360, fill=HAIR)
    # 目・口
    for ex in (-0.38, 0.38):
        d.ellipse([cx + r * ex - r * 0.1, top + r * 1.05, cx + r * ex + r * 0.1, top + r * 1.3], fill=DARK)
    d.arc([cx - r * 0.3, top + r * 1.25, cx + r * 0.3, top + r * 1.65], 20, 160, fill=DARK, width=max(2, int(r * 0.08)))
    if cap:  # 角帽
        lw = max(2, int(r * 0.08))
        d.rectangle([cx - r * 0.8, top + r * 0.0, cx + r * 0.8, top + r * 0.55], fill=DARK, outline=WHITE, width=lw)
        d.polygon([(cx - r * 1.6, top - r * 0.1), (cx, top - r * 0.75), (cx + r * 1.6, top - r * 0.1),
                   (cx, top + r * 0.5)], fill=DARK, outline=WHITE, width=lw)
        d.line([(cx, top - r * 0.12), (cx + r * 1.25, top + r * 0.1), (cx + r * 1.25, top + r * 0.9)],
               fill=GOLD, width=max(2, int(r * 0.12)))
        d.ellipse([cx + r * 1.1, top + r * 0.8, cx + r * 1.4, top + r * 1.1], fill=GOLD)


def icon(name, text=None, size=300):
    """アイコン1つ（size四方くらい）"""
    text = None if text is None else str(text)
    s = size * SS
    im, d = _canvas(size, size)
    c = s / 2
    f = lambda px: _font(int(px * SS))  # noqa: E731
    if name == "calendar":
        d.rounded_rectangle([s * .1, s * .14, s * .9, s * .92], radius=int(s * .08), fill=WHITE)
        d.rounded_rectangle([s * .1, s * .14, s * .9, s * .36], radius=int(s * .08), fill=GREEN)
        d.rectangle([s * .1, s * .28, s * .9, s * .36], fill=GREEN)
        for x in (.3, .7):
            d.rounded_rectangle([s * (x - .035), s * .06, s * (x + .035), s * .22], radius=int(s * .03), fill=NAVY)
        d.text((c, s * .64), text or "", font=f(size * .3 if len(text or "") <= 3 else size * .2), fill=NAVY, anchor="mm")
    elif name == "coin":
        d.ellipse([s * .08, s * .08, s * .92, s * .92], fill=(214, 150, 30))
        d.ellipse([s * .08, s * .04, s * .92, s * .88], fill=GOLD)
        d.ellipse([s * .18, s * .14, s * .82, s * .78], outline=(255, 222, 140), width=int(s * .03))
        t = text or "¥"
        d.text((c, s * .46), t, font=f(size * (.38 if len(t) <= 2 else .26 if len(t) <= 3 else .2)), fill=NAVY, anchor="mm")
    elif name == "document":
        d.polygon([(s * .18, s * .06), (s * .66, s * .06), (s * .82, s * .22), (s * .82, s * .94), (s * .18, s * .94)], fill=WHITE)
        d.polygon([(s * .66, s * .06), (s * .66, s * .22), (s * .82, s * .22)], fill=GRAY)
        d.text((s * .27, s * .17), (text or "通知書")[:6], font=f(size * .09), fill=NAVY, anchor="lm")
        for i, y in enumerate((.36, .48, .6, .72)):
            col = GOLD if i == 2 else GRAY
            d.rounded_rectangle([s * .27, s * y, s * (.73 if i != 3 else .55), s * (y + .05)], radius=int(s * .02), fill=col)
        d.ellipse([s * .56, s * .7, s * .76, s * .9], outline=CORAL, width=int(s * .025))
        d.text((s * .66, s * .8), "確認", font=f(size * .055), fill=CORAL, anchor="mm")
    elif name == "phone":
        d.rounded_rectangle([s * .24, s * .02, s * .76, s * .98], radius=int(s * .08), fill=DARK)
        d.rounded_rectangle([s * .27, s * .08, s * .73, s * .92], radius=int(s * .05), fill=WHITE)
        cols = [CORAL, GREEN, (90, 140, 230), GOLD]
        for i in range(4):
            y = s * (.14 + i * .19)
            d.rounded_rectangle([s * .31, y, s * .41, y + s * .1], radius=int(s * .025), fill=cols[i])
            d.rounded_rectangle([s * .44, y + s * .015, s * .53, y + s * .04], radius=int(s * .01), fill=GRAY)
            d.text((s * .7, y + s * .05), "¥500", font=f(size * .045), fill=NAVY, anchor="rm")
            if i == 1:
                d.line([(s * .3, y + s * .05), (s * .71, y + s * .05)], fill=CORAL, width=int(s * .012))
    elif name in ("student", "worker"):
        _person(d, c, s * .12, s * .16, body=GREEN if name == "student" else NAVY_LIGHT, cap=name == "student",
                tie=name == "worker")
    elif name == "family":
        _person(d, s * .34, s * .1, s * .13, body=GREEN)
        _person(d, s * .66, s * .1, s * .13, body=NAVY_LIGHT, tie=True)
        _person(d, c, s * .44, s * .09, body=GOLD)
    elif name == "building":
        d.polygon([(s * .1, s * .34), (c, s * .1), (s * .9, s * .34)], fill=GREEN)
        d.rectangle([s * .14, s * .34, s * .86, s * .86], fill=WHITE)
        for x in (.24, .4, .56, .72):
            d.rectangle([s * x, s * .42, s * (x + .06), s * .78], fill=GRAY)
        d.rectangle([s * .08, s * .84, s * .92, s * .92], fill=GRAY)
        d.text((c, s * .25), text or "役所", font=f(size * .07), fill=WHITE, anchor="mm")
    elif name == "warning":
        d.polygon([(c, s * .08), (s * .94, s * .86), (s * .06, s * .86)], fill=GOLD)
        d.rounded_rectangle([c - s * .04, s * .32, c + s * .04, s * .62], radius=int(s * .03), fill=NAVY)
        d.ellipse([c - s * .045, s * .68, c + s * .045, s * .77], fill=NAVY)
    elif name == "check":
        d.ellipse([s * .08, s * .08, s * .92, s * .92], fill=GREEN)
        d.line([(s * .28, s * .52), (s * .44, s * .68), (s * .74, s * .36)], fill=WHITE, width=int(s * .09), joint="curve")
    elif name == "cross":
        d.ellipse([s * .08, s * .08, s * .92, s * .92], fill=CORAL)
        for a, b in (((.32, .32), (.68, .68)), ((.68, .32), (.32, .68))):
            d.line([(s * a[0], s * a[1]), (s * b[0], s * b[1])], fill=WHITE, width=int(s * .09))
    elif name == "wallet":
        d.ellipse([s * .48, s * .1, s * .78, s * .4], fill=GOLD)
        d.text((s * .63, s * .25), "¥", font=f(size * .14), fill=NAVY, anchor="mm")
        d.rounded_rectangle([s * .1, s * .3, s * .9, s * .86], radius=int(s * .08), fill=GREEN)
        d.rounded_rectangle([s * .6, s * .48, s * .94, s * .68], radius=int(s * .05), fill=(30, 140, 95))
        d.ellipse([s * .68, s * .54, s * .76, s * .62], fill=GOLD)
    elif name == "gift":
        d.rectangle([s * .14, s * .4, s * .86, s * .9], fill=GREEN)
        d.rectangle([s * .1, s * .3, s * .9, s * .44], fill=(40, 190, 130))
        d.rectangle([c - s * .06, s * .3, c + s * .06, s * .9], fill=GOLD)
        d.ellipse([c - s * .26, s * .1, c, s * .32], outline=GOLD, width=int(s * .05))
        d.ellipse([c, s * .1, c + s * .26, s * .32], outline=GOLD, width=int(s * .05))
    elif name == "pension":  # 年金手帳
        d.rounded_rectangle([s * .2, s * .08, s * .8, s * .92], radius=int(s * .05), fill=(70, 120, 210))
        d.rectangle([s * .2, s * .08, s * .28, s * .92], fill=(50, 95, 180))
        d.text((s * .54, s * .36), "年金", font=f(size * .13), fill=WHITE, anchor="mm")
        d.ellipse([s * .42, s * .52, s * .66, s * .76], outline=GOLD, width=int(s * .02))
    elif name == "chat":
        d.rounded_rectangle([s * .08, s * .16, s * .92, s * .7], radius=int(s * .12), fill=WHITE)
        d.polygon([(s * .26, s * .66), (s * .44, s * .66), (s * .22, s * .86)], fill=WHITE)
        d.text((c, s * .43), text or "?", font=f(size * (.22 if len(text or "?") <= 3 else .13)), fill=NAVY, anchor="mm")
    else:
        raise ValueError(f"未知のアイコン: {name}")
    return _done(im)


NAVY_LIGHT = (52, 86, 140)


# ---------- 図解クラス ----------
def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def ease_back(x):
    x = max(0.0, min(1.0, x))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


def _fade(im, a):
    if a >= 1:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0, a))))
    return im


def _scaled(im, k):
    if abs(k - 1) < 0.01:
        return im
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.BILINEAR)


def _caption(text, size=62, color=WHITE):
    from .render import render_telop
    return render_telop(text, max_size=size, min_size=28)


class Visual:
    """frame(lt) で W x AREA_H のRGBA画像を返す"""

    def __init__(self, spec):
        self.spec = spec
        self.setup()

    def setup(self):
        pass

    def canvas(self):
        return Image.new("RGBA", (W, AREA_H), (0, 0, 0, 0))


class IconVisual(Visual):
    def setup(self):
        sp = self.spec
        self.img = _shadow(icon(sp["name"], sp.get("text"), size=sp.get("size", 400)))
        self.cap = _caption(str(sp["caption"])) if sp.get("caption") else None

    def frame(self, lt):
        im = self.canvas()
        k = 0.6 + 0.4 * ease_back(lt / 0.35)
        bob = math.sin(lt * 2.6) * 8
        ic = _fade(_scaled(self.img, k), lt / 0.15)
        h = AREA_H - (70 if self.cap else 0)
        im.alpha_composite(ic, (int(W / 2 - ic.width / 2), int(h / 2 - ic.height / 2 + bob)))
        if self.cap:
            c = _fade(self.cap, (lt - 0.25) / 0.2)
            im.alpha_composite(c, (int(W / 2 - c.width / 2), AREA_H - c.height + 10))
        return im


class IconsVisual(Visual):
    def setup(self):
        items = self.spec["items"]
        n = len(items)
        size = min(320, int((W - 120) / n / 1.02))
        self.imgs = [_shadow(icon(it["name"], it.get("text"), size=size), off=6, blur=8) for it in items]
        self.labels = [_caption(it["label"], size=52) if it.get("label") else None for it in items]
        self.ops = self.spec.get("ops")  # 例: ["+", "+", "="]
        self.cap = _caption(self.spec["caption"]) if self.spec.get("caption") else None

    def frame(self, lt):
        im = self.canvas()
        n = len(self.imgs)
        step = (W - 120) / n
        h = AREA_H - (80 if self.cap else 0)
        for i, ic in enumerate(self.imgs):
            t = lt - i * 0.12
            if t <= 0:
                continue
            k = 0.5 + 0.5 * ease_back(t / 0.3)
            ic2 = _fade(_scaled(ic, k), t / 0.12)
            cx = 60 + step * (i + 0.5)
            iy = h / 2 - ic2.height / 2 - (30 if self.labels[i] else 0)
            im.alpha_composite(ic2, (int(cx - ic2.width / 2), int(iy)))
            lb = self.labels[i]
            if lb is not None:
                lb = _fade(lb, (t - 0.15) / 0.2)
                im.alpha_composite(lb, (int(cx - lb.width / 2), int(h / 2 + ic.height / 2 - 70)))
        if self.cap:
            c = _fade(self.cap, (lt - 0.12 * n) / 0.2)
            im.alpha_composite(c, (int(W / 2 - c.width / 2), AREA_H - c.height + 10))
        return im


class BarVisual(Visual):
    def setup(self):
        self.items = self.spec["items"]
        vmax = max(float(it["value"]) for it in self.items) or 1
        self.ratios = [float(it["value"]) / vmax for it in self.items]

    def frame(self, lt):
        im, d = _canvas(W, AREA_H)
        n = len(self.items)
        bw = min(260, (W - 300) / n) * SS
        gap = min(140 * SS, (W * SS - 200 * SS - bw * n) / max(1, n - 1)) if n > 1 else 0
        x0 = (W * SS - (bw * n + gap * (n - 1))) / 2
        base = (AREA_H - 70) * SS
        top_max = 90 * SS
        d.line([(80 * SS, base), ((W - 80) * SS, base)], fill=(255, 255, 255, 120), width=3 * SS)
        for i, it in enumerate(self.items):
            t = ease((lt - 0.1 - i * 0.18) / 0.5)
            hi = it.get("highlight")
            r = max(self.ratios[i], 0.02)
            h = (base - top_max) * r * t
            x = x0 + i * (bw + gap)
            col = GOLD if hi else (255, 255, 255, 110)
            if h > 2:
                d.rounded_rectangle([x, base - h, x + bw, base], radius=int(16 * SS), fill=col)
            d.text((x + bw / 2, base + 38 * SS), it.get("label", ""), font=_font(40 * SS), fill=WHITE, anchor="mm")
            if t > 0.6:
                txt = it.get("text", "")
                a = int(255 * min(1, (t - 0.6) / 0.3))
                d.text((x + bw / 2, base - h - 34 * SS), txt, font=_font((50 if hi else 42) * SS),
                       fill=(GOLD if hi else WHITE) + (a,), anchor="mm", stroke_width=6 * SS, stroke_fill=NAVY + (a,))
        if self.spec.get("arrow") and lt > 0.9:  # 増えた/減ったを示す矢印
            a = int(255 * min(1, (lt - 0.9) / 0.3))
            col = CORAL + (a,) if self.spec["arrow"] == "down" else GREEN + (a,)
            d.text((W * SS / 2, top_max - 20 * SS), "▼" if self.spec["arrow"] == "down" else "▲", font=_font(40 * SS),
                   fill=col, anchor="mm")
        return _done(im)


class CompareVisual(Visual):
    def setup(self):
        sp = self.spec
        self.left = self._card(sp.get("before_label", "これまで"), sp["before"], False)
        self.right = self._card(sp.get("after_label", "これから"), sp["after"], True)

    def _card(self, label, value, hi):
        w, h = 420, 320
        im, d = _canvas(w, h)
        s = SS
        d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=36 * s,
                            fill=(GREEN + (255,)) if hi else (255, 255, 255, 46))
        d.text((w * s / 2, 64 * s), label, font=_font(40 * s), fill=WHITE, anchor="mm")
        size = 92
        while size > 40 and _font(size * s).getlength(value) > (w - 50) * s:
            size -= 2
        d.text((w * s / 2, 180 * s), value, font=_font(size * s), fill=GOLD if hi else WHITE, anchor="mm",
               stroke_width=(6 if hi else 0) * s, stroke_fill=NAVY)
        if not hi:
            d.line([(70 * s, 182 * s), ((w - 70) * s, 182 * s)], fill=CORAL, width=8 * s)
        return _shadow(_done(im), off=8, blur=10, alpha=90)

    def frame(self, lt):
        im = self.canvas()
        cy = AREA_H / 2
        l = _fade(self.left, lt / 0.2)
        lpad = (l.width - 420) / 2
        im.alpha_composite(l, (int(W / 2 - 55 - 420 - lpad - 40 * (1 - ease(lt / 0.3))), int(cy - l.height / 2)))
        if lt > 0.3:
            d = ImageDraw.Draw(im)
            a = min(1, (lt - 0.3) / 0.2)
            x = W / 2 + 6 * math.sin(lt * 6)
            d.polygon([(x - 22, cy - 30), (x + 22, cy), (x - 22, cy + 30)], fill=GOLD + (int(255 * a),))
        if lt > 0.45:
            t = lt - 0.45
            r = _scaled(self.right, 0.7 + 0.3 * ease_back(t / 0.35))
            r = _fade(r, t / 0.15)
            im.alpha_composite(r, (int(W / 2 + 55 + 210 - r.width / 2), int(cy - r.height / 2)))
        return im


class MonthsVisual(Visual):
    def setup(self):
        self.hl = set(self.spec.get("highlight", []))
        self.cap = _caption(self.spec["caption"]) if self.spec.get("caption") else None

    def frame(self, lt):
        im, d = _canvas(W, AREA_H)
        s = SS
        box, gap = 140, 20
        x0 = (W - (box * 6 + gap * 5)) / 2
        for i in range(12):
            m = i + 1
            row, col = divmod(i, 6)
            x = (x0 + col * (box + gap)) * s
            y = (20 + row * (box + gap)) * s
            on = m in self.hl and lt > 0.15 + 0.06 * i
            fill = GREEN if on else (255, 255, 255, 40)
            d.rounded_rectangle([x, y, x + box * s, y + box * s], radius=24 * s, fill=fill)
            d.text((x + box * s / 2, y + box * s / 2), f"{m}月", font=_font(40 * s),
                   fill=WHITE if on else (255, 255, 255, 150), anchor="mm")
        out = _done(im)
        if self.cap:
            c = _fade(self.cap, (lt - 0.6) / 0.2)
            out.alpha_composite(c, (int(W / 2 - c.width / 2), AREA_H - c.height + 10))
        return out


class StepsVisual(Visual):
    def setup(self):
        self.rows = []
        for i, text in enumerate(self.spec["items"], 1):
            w, h = 920, 124
            im, d = _canvas(w, h)
            s = SS
            d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=62 * s, fill=(255, 255, 255, 235))
            d.ellipse([12 * s, 12 * s, 112 * s, 112 * s], fill=GREEN)
            d.text((62 * s, 62 * s), str(i), font=_font(54 * s), fill=WHITE, anchor="mm")
            d.text((138 * s, 62 * s), text, font=_font(52 * s), fill=NAVY, anchor="lm")
            self.rows.append(_done(im))

    def frame(self, lt):
        im = self.canvas()
        n = len(self.rows)
        gap = 18
        total = n * 124 + (n - 1) * gap
        y0 = (AREA_H - total) / 2
        for i, r in enumerate(self.rows):
            t = lt - 0.1 - i * 0.22
            if t <= 0:
                continue
            x = W / 2 - r.width / 2 + 80 * (1 - ease(t / 0.3))
            im.alpha_composite(_fade(r, t / 0.15), (int(x), int(y0 + i * (124 + gap))))
        return im


TYPES = {"icon": IconVisual, "icons": IconsVisual, "bar": BarVisual, "compare": CompareVisual,
         "months": MonthsVisual, "steps": StepsVisual}


def make(spec):
    if not spec:
        return None
    t = spec.get("type", "icon")
    if t not in TYPES:
        raise ValueError(f"未知の visual type: {t}（{' / '.join(TYPES)}）")
    return TYPES[t](spec)


# ---------- エンディング（保存＋フォロー） ----------
class FollowCTA:
    """アカウントのアイコン＋フォローボタン（押される演出つき）"""

    def __init__(self):
        w, h = 760, 170
        im, d = _canvas(w, h)
        s = SS
        d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=85 * s, fill=(255, 255, 255, 240))
        # アバター
        d.text((180 * s, 62 * s), config.ACCOUNT_NAME, font=_font(42 * s), fill=NAVY, anchor="lm")
        d.text((180 * s, 112 * s), "毎日お得情報を発信中", font=_font(30 * s), fill=(90, 100, 120), anchor="lm")
        card = _done(im)
        card.alpha_composite(avatar(138), (16, 16))
        self.card = _shadow(card, off=8, blur=12, alpha=100)
        self.btn = self._button(False)
        self.btn_done = self._button(True)

    def _button(self, done):
        w, h = 300, 112
        im, d = _canvas(w, h)
        s = SS
        d.rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=56 * s, fill=GREEN if done else CORAL)
        d.text((w * s / 2, h * s / 2), "フォロー中 ✓" if done else "＋ フォロー", font=_font(44 * s), fill=WHITE,
               anchor="mm")
        return _shadow(_done(im), off=6, blur=8, alpha=90)

    def frame(self, lt):
        im = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
        if lt <= 0:
            return im
        c = _fade(self.card, lt / 0.2)
        cy = 30 + 30 * (1 - ease(lt / 0.3))
        im.alpha_composite(c, (int(W / 2 - c.width / 2), int(cy)))
        bt = lt - 0.35
        if bt > 0:
            pressed = bt > 1.1
            b = self.btn_done if pressed else self.btn
            pulse = 1 + 0.06 * math.sin(bt * 7) if not pressed else 1.0
            if 1.0 < bt < 1.15:
                pulse = 0.9
            b = _fade(_scaled(b, pulse * (0.6 + 0.4 * ease_back(bt / 0.3))), bt / 0.15)
            by = 30 + self.card.height - 20
            im.alpha_composite(b, (int(W / 2 - b.width / 2), int(by)))
            if 0.5 < bt < 1.6:  # 指アイコン
                hx = W / 2 + 90 - 40 * ease((bt - 0.5) / 0.5)
                hy = by + 80 - 30 * ease((bt - 0.5) / 0.5)
                d = ImageDraw.Draw(im)
                d.ellipse([hx, hy, hx + 56, hy + 56], fill=(255, 255, 255, 230), outline=NAVY, width=4)
                d.ellipse([hx + 18, hy + 18, hx + 38, hy + 38], fill=NAVY)
        return im
