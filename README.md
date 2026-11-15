# 「〇〇県民しか知らないこと3選」ショート動画ジェネレーター

縦型ショート動画（1080x1920 / 30fps / 30〜40秒 / mp4）を、県ごとの台本YAMLから自動生成します。

## 使い方
```bash
pip install -r requirements.txt          # ffmpeg も必要
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

シリーズ全体の見出し・声の速さ・BGM音量などは `series.yaml` で変更できます。

## 素材とライセンス
- ナレーション: Open JTalk（pyopenjtalk-plus, 修正BSD）
- BGM: スクリプト内で自作したシンセ音（著作権フリー）
- フォント: M PLUS Rounded 1c（SIL OFL 1.1）
- 地図: 地球地図日本（国土地理院）— 動画内に出典を表示。**営利目的で使う場合は国土地理院への利用報告が必要**（`assets/geo/SOURCE.md`）
