# 知らなきゃ損ラボ ショート動画メーカー

台本YAMLを `scripts/` に置くだけで、TikTok用の縦動画（1080x1920 / 30fps / mp4）と投稿用キャプションを書き出します。

## セットアップ
```bash
pip install -r requirements.txt
apt-get install -y ffmpeg fonts-noto-cjk fonts-noto-cjk-extra
```

## 使い方
```bash
python make_videos.py --check                         # 全台本のルールチェック
python make_videos.py scripts/001_juminzei_2nenme.yaml # 1本書き出し
python make_videos.py FILE --preview                  # 静止画プレビューだけ（数秒）
python make_videos.py --batch                         # status: approved の未書き出し分を7本まとめて
python make_videos.py --batch --include-draft --force # 下書き含め作り直し
```
出力は `out/<台本名>/` に `*.mp4`・`cover.png`・`caption.txt`（キャプション＋ハッシュタグ＋出典チェック欄）。

## 台本の書き方
`scripts/001_juminzei_2nenme.yaml` を参照。
- `length`: `short`（20〜40秒・ポイント1つ）/ `long`（60〜75秒・ポイント3つ、point に `number: 1〜3`）
- `targets`: 学生・若者 / 新社会人 / 一人暮らし / 30〜40代 / 季節
- `info_year`・`sources`（公式URL）は必須。不確かな行には `check: 要確認`
- `scenes[].role`: hook / who / point / caution / outro
- テロップは `[[...]]` で金色強調、`\n` で改行（1行15文字以内）
- 読み間違いは `reading:` に読みを書く
- `status: approved` にした台本だけが `--batch` の対象

## ナレーション
- 既定: OpenJTalk（pipだけで動く）
- 推奨: VOICEVOX（`lab/config.py` の `TTS_BACKEND = "voicevox"`）。利用時はキャプションにクレジット（例「VOICEVOX:春日部つむぎ」）が自動で入ります。

BGM・効果音はすべて `lab/audio.py` でコード生成（著作権フリー）。
