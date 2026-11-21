# アニメコント動画

## 動画を作るコマンド
```
bash tools/start_voicevox.sh        # 声のエンジンを起動（初回のみ）
python3 tools/make_placeholders.py  # 仮の絵・効果音・BGMを用意（既存ファイルは上書きしない）
python3 tools/make_video.py         # script/script.json → output/video.mp4
```
- 台本: `script/script.json`（セリフ・演出）
- 配役: `script/cast.json`（声・色・立ち位置・タイトル）
- 概要欄のクレジットは `output/video_credits.txt` に自動で出ます
