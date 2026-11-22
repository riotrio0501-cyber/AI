# Gonta & Piko（動物コント・縦型ショート）

## 1本作る手順
1. `episodes/<番号_名前>/storyboard.json` にカット割りを書く（1本目をコピーして書きかえる）
2. `python3 tools/episode.py plan episodes/<番号_名前>` → 生成用プロンプトと必要クレジットが出る
3. Higgsfield で生成し、`frames/cNN.png`（静止画）・`clips/cNN.mp4`（動画）として保存
4. `python3 tools/episode.py build episodes/<番号_名前>` → `output/<番号_名前>.mp4` が完成

素材がまだ無いカットは仮の絵で埋まるので、生成前でも尺・テロップ・音の確認ができる。

## ファイル
- `characters/prompts.json` … キャラの見た目文章・絵のタッチ・NGワード・参照画像ID（固定）
- `tools/make_sfx.py` … 効果音とBGMを自作（`assets/se`, `assets/bgm` に出力）
- `tools/episode.py` … plan（見積もり）と build（編集・書き出し）

## 静止画の動き（storyboard.json の motion）
`static` / `slow_push`（ゆっくり寄る）/ `zoom_in` / `punch_zoom`（ドンッと寄る）/ `shake`（フラフラ揺れ）

## 効果音の名前（storyboard.json の se）
snore, small_snore, pop_in, whoosh, tada, tick, alarm, rustle_thud, clang, deflate, eye_pop, slide_down, tumble, snow_poof
