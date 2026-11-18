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
4. ネタごとに `evidence`（出典URL・メモ）と `status` を書く
   - `ok`＝根拠あり / `説`＝確定していないので「〜という説」「〜という人も多い」と言い方で逃がす / `要確認`＝未確認（警告が出る）
   - `comment_question` に「どっち派？」の問いを書くと、締めのテロップと投稿文に入る（コメント狙い）
5. `--check` で尺（30〜40秒）と警告を確認してから生成

シリーズ全体の見出し・声・BGM音量などは `series.yaml` で変更できます。

## 写真を入れる
ネタごとに `photo:` を書くと、画面上部に写真カード（ゆっくりズーム）が出て、テロップはその下に移動します。
```yaml
  - title: "芋煮は地域で別物"
    photo: assets/photos/yamagata/imoni.jpg          # 1枚
    # photo: [assets/photos/a.jpg, assets/photos/b.jpg]  # 複数なら順に切り替え
    # photo: {emoji: "🍜"}                            # 写真がないときは絵文字カード
    # photo: {file: assets/photos/x.jpg, focus: [0.5, 0.3]}  # 切り抜きの中心（0〜1）
```
Wikimedia Commons から取り込むとライセンスとクレジットが `.json` に保存され、写真の右下と投稿文に自動で入ります。
```bash
python photos.py search "せり鍋"                                       # 候補（ライセンス付き）を一覧
python photos.py get "File:Serinabe.jpg" assets/photos/miyagi/serinabe.jpg  # 取り込み
```
- 使うライセンスは CC0 / パブリックドメイン / CC BY / CC BY-SA のみ（それ以外は get が拒否）
- Wikimedia は回数制限が厳しいので、ツールは3秒に1回のペースで、標準サイズのサムネイルだけを取得します
- 自分で撮った写真は `assets/photos/` に置いて `photo:` に書くだけ（クレジット不要。必要なら `credit:` を書く）

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
- 写真: Wikimedia Commons（各写真の作者・ライセンスは `assets/photos/*/*.json`）。CC BY-SA の写真を使った動画は、厳密には動画にも CC BY-SA の条件（表示・継承）がかかる点に注意
- 地図: 地球地図日本（国土地理院）— 動画内に出典を表示。**営利目的で使う場合は国土地理院への利用報告が必要**（`assets/geo/SOURCE.md`）
