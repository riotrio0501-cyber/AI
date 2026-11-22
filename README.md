# 氷河期どうぶつコント（3D CGアニメ風・縦型ショート）

オリジナルキャラ「ゴロ・ピピ・ドンさん」が氷と雪の世界でドタバタする、セリフなしの縦型ショート動画をAIで作るプロジェクト。

## いまの状況

| 工程 | 状況 |
|---|---|
| キャラ設定 `characters.md` | ✅ 作成済み（プロンプト用の英文つき） |
| 1本目のカット割り `storyboard/001_last_berry/` | ✅ 9カット・44秒 |
| 生成プロンプト（コピペ用） | ✅ `storyboard/001_last_berry/prompts.md`、設定画用 `assets/characters/prompts.md` |
| 効果音18種＋BGM1曲 | ✅ プログラムで自作（権利の心配なし・クレジット表記不要）。くしゃみだけ仮 |
| 自動編集スクリプト | ✅ 絵コンテ動画 `output/001_last_berry_animatic.mp4` で動作確認済み |
| 作り方 | **無料の3Dソフト Blender で作る方式（C案）** に決定 |
| 3人の3Dモデル `tools/blender/characters.py` | ✅ 試作版。設定画 `assets/characters/*_3d_sheet.png`, `lineup_3d.png` |
| 動き（アニメーション）と各カットの映像 | ⏳ キャラのOKが出たら着手 |

## 作り方（毎回の流れ）

```bash
pip install -r requirements.txt        # 最初の1回だけ（Blenderのpython版など）
python3 tools/blender/sheet.py goro       # 設定画（goro / pipi / don）
python3 tools/blender/sheet_all.py        # 3人の並び
python3 tools/make_sounds.py              # 効果音・BGMを作る（最初の1回だけ）
python3 tools/prompts.py --sheets         # 設定画のプロンプトを作る
python3 tools/prompts.py 001_last_berry   # 各カットのプロンプトを作る
python3 tools/assemble.py 001_last_berry  # つないで完成動画 → output/
```

- `assets/frames/<ネタ>/c01.png` を置くと、そのカットは静止画に置き換わる
- `assets/clips/<ネタ>/c01.mp4` を置くと、そのカットは動画に置き換わる
- 何もないカットは「仮カード」で表示される → いつでも全体の尺とテンポを確認できる
- 新しいネタは `storyboard/<番号_名前>/storyboard.md` をコピーして書き換えるだけ

## フォルダ

```
characters.md          キャラ設定（プロンプトの元。ここを直すと全部に反映）
storyboard/            カット割り表（ネタごと）
assets/characters/     設定画
assets/frames/         各カットの最初の1枚
assets/clips/          生成した動画クリップ
assets/bgm/ assets/se/ BGM・効果音（商用OKのみ）
assets/sound_credits.yaml  音素材のクレジット台帳（未登録の音は使えない仕組み）
output/                完成動画とクレジット一覧
tools/                 スクリプト
```
