"""台本YAMLの読み込みとルールチェック"""
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from . import config

GOLD_RE = re.compile(r"\[\[(.+?)\]\]")
ROLES = {"hook", "who", "point", "caution", "outro"}


@dataclass
class Scene:
    role: str
    telop: str
    narration: str
    reading: str | None = None  # TTS用の読み（読み間違い対策）
    number: int | None = None   # longのポイント番号
    check: str | None = None
    visual: dict | None = None  # 図解・イラスト（lab/visuals.py 参照）


@dataclass
class Script:
    path: Path
    id: str
    title: str
    length: str
    targets: list
    info_year: str
    status: str
    sources: list
    scenes: list
    caption: str
    hashtags: list
    season: int | None = None
    age_note: str | None = None
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def slug(self):
        return self.path.stem


def plain(telop: str) -> str:
    return GOLD_RE.sub(r"\1", telop)


def load(path) -> Script:
    path = Path(path)
    d = yaml.safe_load(path.read_text(encoding="utf-8"))
    scenes = [Scene(**{k: v for k, v in s.items() if k in Scene.__dataclass_fields__}) for s in d.get("scenes", [])]
    s = Script(
        path=path, id=str(d.get("id", path.stem)), title=d.get("title", ""), length=d.get("length", "short"),
        targets=d.get("targets") or [], info_year=str(d.get("info_year") or ""), status=d.get("status", "draft"),
        sources=d.get("sources") or [], scenes=scenes, caption=(d.get("caption") or "").strip(),
        hashtags=d.get("hashtags") or [], season=d.get("season"), age_note=d.get("age_note"),
    )
    validate(s)
    return s


def validate(s: Script):
    E, Wn = s.errors, s.warnings
    if s.length not in config.LENGTH_RULES:
        E.append(f"length は short / long のどちらか（今: {s.length}）")
    for t in s.targets:
        if t not in config.TARGETS:
            Wn.append(f"対象タグ「{t}」は定義外（{' / '.join(config.TARGETS)}）")
    if not s.targets:
        E.append("targets（対象）が空")
    if not s.info_year:
        E.append("info_year（何年度の情報か）が未記入")
    if not s.sources:
        E.append("sources（出典URL）が空")
    for src in s.sources:
        url = src.get("url", "") if isinstance(src, dict) else str(src)
        if not url.startswith("http"):
            E.append(f"出典URLが不正: {url}")
    if not s.scenes:
        E.append("scenes が空")
    else:
        if s.scenes[0].role != "hook":
            Wn.append("最初のシーンが hook ではない")
        if s.scenes[-1].role != "outro":
            Wn.append("最後のシーンが outro ではない")
        if not any(sc.role == "caution" for sc in s.scenes):
            Wn.append("注意点（caution）シーンがない")
        if s.length == "long":
            nums = {sc.number for sc in s.scenes if sc.role == "point" and sc.number}
            if nums != {1, 2, 3}:
                Wn.append(f"long はポイント番号 1〜3 が必要（今: {sorted(nums)}）")
    for i, sc in enumerate(s.scenes, 1):
        if sc.role not in ROLES:
            E.append(f"シーン{i}: role「{sc.role}」は不明（{' / '.join(sorted(ROLES))}）")
        for line in plain(sc.telop).split("\n"):
            if len(line) > 15:
                Wn.append(f"シーン{i}: テロップ1行が{len(line)}文字（15文字以内推奨）「{line}」")
        if sc.check:
            Wn.append(f"シーン{i}: 要確認 → {sc.check}" if sc.check != "要確認" else f"シーン{i}: 要確認")
    from .visuals import TYPES
    for i, sc in enumerate(s.scenes, 1):
        if sc.visual and sc.visual.get("type", "icon") not in TYPES:
            E.append(f"シーン{i}: visual type「{sc.visual.get('type')}」は不明（{' / '.join(TYPES)}）")
    if s.scenes and s.scenes[-1].role == "outro" and "フォロー" not in s.scenes[-1].narration:
        Wn.append("最後のシーンでフォローを促していない")
    text = " ".join([s.caption] + [sc.narration + sc.telop for sc in s.scenes])
    for w in config.NG_WORDS:
        if w in text:
            Wn.append(f"NGワード候補「{w}」（断定・金融商品の推奨になっていないか確認）")
    if "要確認" in text:
        Wn.append("本文に「要確認」が残っている")
