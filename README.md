# 「〇〇県民しか知らないこと3選」ショート動画ジェネレーター

縦型ショート動画（1080x1920 / 30fps / 30〜40秒 / mp4）を、県ごとの台本YAMLから自動生成します。

## 使い方
```bash
pip install -r requirements.txt          # ffmpeg も必要
pip install --no-deps style-bert-vits2   # 自然な声（Style-Bert-VITS2）用
python make_video.py prefectures/yamagata.yaml          # → out/yamagata.mp4
python make_video.py prefectures/yamagata.yaml --check  # 台本チェックと尺だけ
python make_video.py --all                              # prefectures/*.yaml を全部
python make_video.py --all --strict                     # 「要確認」が残る県は作らない
```

## 新しい県を追加する
1. `prefectures/yamagata.yaml` をコピーして `prefectures/<県名ローマ字>.yaml` を作る
2. `prefecture`（県名）、`code`（JIS都道府県コード、例: 青森=2）、`color.main`（イメージカラー）を書き換える
3. フック・ネタ3つ・締めの `narration`（読み上げ）と `captions`（テロップ）を書く
   - `[ ]`＝県カラー、`{ }`＝強調の黄、`/`＝改行位置（省略すると自動）
   - 読みを直したいときは `reading` に読み上げ用テキストを書く
4. ネタごとに `evidence`（出典URL・メモ）と `status: ok / 要確認` を書く
5. `--check` で尺（30〜40秒）と警告を確認してから生成

シリーズ全体の見出し・声・BGM音量などは `series.yaml` で変更できます。

## 声の切り替え
`series.yaml` の `voice:` で選びます（県ファイルに `voice:` を書けば県ごとに上書き）。
- `engine: sbv2` … Style-Bert-VITS2。人間に近い自然な声（初回に Hugging Face から声モデルとBERT 約1.5GBを `models/` にダウンロード。CPUで10秒の音声に約9秒）
  - `model`: `koharune-ami`（女性・既定）/ `jvnv-F1-jp` `jvnv-F2-jp`（女性）/ `jvnv-M1-jp` `jvnv-M2-jp`（男性）
  - `style`: 声の感情スタイル（`Neutral` など。モデルごとに異なる）
  - `speed`: 1.0 が標準
- `engine: openjtalk` … 軽量・高速だが機械的な声

## 素材とライセンス
- ナレーション: Style-Bert-VITS2（AGPL-3.0, ローカル実行のみ）
  - 小春音アミ: [あみたろの声素材工房の規約](https://amitaro.net/voice/voice_rule/)に従えば商用可。**公開時はクレジット必須**（動画内と `out/<県>_投稿文.txt` に自動で入る）
  - JVNVモデル: CC BY-SA 4.0
  - 予備: Open JTalk（pyopenjtalk-plus, 修正BSD）
- BGM: スクリプト内で自作したシンセ音（著作権フリー）
- フォント: M PLUS Rounded 1c（SIL OFL 1.1）
- 地図: 地球地図日本（国土地理院）— 動画内に出典を表示。**営利目的で使う場合は国土地理院への利用報告が必要**（`assets/geo/SOURCE.md`）
