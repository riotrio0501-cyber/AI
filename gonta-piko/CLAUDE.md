# Gonta & Piko（動物コント・縦型ショート）制作プロジェクト

## このプロジェクトの目的
雪山に住むオリジナルの動物キャラが、セリフなしでドタバタする
3DCGアニメ映画風のショート動画を、AIで作って YouTube チャンネル「Gonta & Piko」で投稿する。
目標は YouTube の収益化（YPP参加）。

私（ユーザー）は動画編集やプログラミングの専門家ではないので、
作業は基本的にあなた（Claude Code）が進め、私には要点だけ短く確認してほしい。
説明は専門用語を避けて、短く分かりやすく。

## 大事な前提
- この企画は新しく始めるもの。リポジトリ内の `claude/3d-animal-comedy-shorts-*` ブランチの企画（ゴロ・ピピ・ドンさん）は使わない。参考にもしない
- 既存のアニメ映画（特にアイス・エイジ）のキャラ・名前・有名なギャグに似せない。プロンプトに作品名・キャラ名・スタジオ名・「〜風」を書かない
- どんぐりを追いかけるリス、マンモス、ナマケモノ、サーベルタイガーは出さない

## 動画の形
- 縦型 9:16（1080×1920）、1本 約30秒
- **セリフなし**（映像＋効果音＋BGM＋短いテロップだけ）。海外の人にも伝わるようにする
- 最初の1秒で何か起きる。オチで1カット目に戻る（ループする）形をなるべく使う
- 構成は「動画カット」と「静止画カット（ズーム・揺れ・効果音で動きを出す）」を混ぜて、お金を抑える

## キャラクター（固定。見た目は毎回この文章をそのまま使う）

### ゴンタ（ツキノワグマ・大きい方）
- まん丸の体、黒い毛、胸に白い三日月もよう、いつも眠そうな半目、**赤いマフラー**（目じるし）
- 性格：のんびり食いしん坊。どこでも3秒で寝る
- お約束：驚くと体ごと雪に「ぼふっ」と埋まる

```prompt:gonta
Gonta, an original chubby round Asian black bear character, thick fluffy black fur, a cream-white crescent mark on the chest, sleepy half-closed eyes, small tan muzzle, a bright red knitted scarf, big and slow, very expressive face
```

### ピコ（オコジョ・小さい方）
- 真っ白な冬毛、細長い体、**しっぽの先だけ黒**（目じるし）、黒い丸い目
- 性格：しっかり者の世話焼き。いつも頑張るのに報われない
- お約束：怒ると毛が逆立って、体が2倍にふくらむ

```prompt:piko
Piko, an original small slender stoat in pure white winter fur, only the tip of the tail is black, shiny round black eyes, tiny pink nose, small round ears, energetic and expressive, about one fifth the size of Gonta
```

### じい（カモシカの長老・ときどき登場）
- 茶色の毛、短い角、長い白いあごひげ、眠そうな目、いつも同じ岩の上にいる
- お約束：最後に出てきて全部持っていく（オチ担当）

```prompt:jii
Jii, an original elderly Japanese serow with brown shaggy fur, short dark horns, a long white beard, sleepy wise eyes, always sitting calmly on the same snowy rock
```

### 共通の絵のタッチ
```prompt:style
high-end 3D animated feature film still, stylized cartoon proportions, detailed soft fur, glossy expressive eyes, exaggerated squash-and-stretch facial expressions, snowy Japanese mountain forest, bright cinematic light, vivid colors, vertical 9:16 composition, family-friendly slapstick comedy, no text
```

### 入れてほしくないもの
```prompt:negative
text, letters, subtitles, logo, watermark, humans, extra limbs, deformed face, squirrel, acorn, mammoth, sloth, saber-toothed cat
```

## 使うツール
- **動画**：Higgsfield の **MiniMax H3 だけ**を使う（`minimax_h3`）。1秒2クレジット（5秒＝10、15秒＝30）
- **静止画**：Higgsfield の MiniMax H3 Image（`minimax_h3_image`、1k、1枚3クレジット）
- **【例外】Higgsfield 3日間無料お試し中だけ**（ユーザー了承済み 2026-11-23）：
  無制限の対象モデルを使ってよい。画像＝Nano Banana Pro（なければ GPT Image / Seedream 5 Pro）、動画＝Seedance 2.5（720p、生成音声はオフ）。
  キャラの見た目・絵のタッチの文章は変えない。お試しが終わったら MiniMax H3 に戻す。
  お試しは終了前にキャンセルしないと自動で Ultra（初月$75→$129/月）になる。終了前に必ずユーザーに知らせる
- **編集**：ffmpeg（Pythonも可）。効果音・BGMは自作するか、商用利用可でクレジット条件がはっきりした素材だけ使う
- 毎回の作業は `tools/` にスクリプトとして残し、次からは「カット割りを差し替えてコマンド1つで動画ができる」状態にする

## お金のルール（重要）
- **なるべくお金をかけない**。1本あたり約40クレジット以内が目安
- 生成する前に、必ずかかるクレジットを見積もって私に確認する
- 動きの確認は5秒で試してから本番を作る
- 有料サービスの追加・プラン変更・ファイル削除などの大きな判断は、必ず事前に私に確認する

## 1本目：「春なのに起きない」（約28秒）

| # | 秒 | 何が起きるか | 作り方 |
|---|---|---|---|
| 1 | 5 | 雪解けの春。ほら穴で、鼻ちょうちんを出して大いびきのゴンタ。テロップ「春なのに起きない」 | 動画 |
| 2 | 3 | ピコが目覚まし時計を10個並べてドヤ顔 | 静止画＋ズーム |
| 3 | 5 | 全部同時に鳴る。ピコは耳をふさいで転がり、ゴンタは寝返りをうつだけ | 動画 |
| 4 | 3 | ピコ、フライパンとおたまを持ってヘトヘト | 静止画＋揺れ |
| 5 | 3 | ピコ、ゴンタのお腹の上で寝落ち | 静止画 |
| 6 | 5 | ゴンタがパチッと起きて大あくび。お腹からピコが転がり落ちる | 動画 |
| 7 | 4 | オチ：岩の上のじいが時計を1個拾って耳に当てる。手前でピコが1カット目と同じ鼻ちょうちんで寝ている（1カット目に戻ってループ） | 静止画＋効果音 |

コストの目安：動画3カット30クレジット＋静止画4枚12クレジット＝約42クレジット

## ネタのストック（2本目以降の候補）
- 最後のひと口：ゴンタがくしゃみで焼き芋を飛ばす → 追いかけて雪山を転がる → ふもとでじいが食べる
- かまくら建築：ピコが完璧なかまくらを完成 → ゴンタが寄りかかって全壊、ピコの顔だけ雪から出ている
- 自撮りチャレンジ：何度やっても鼻のドアップ → やっと撮れた1枚の後ろに雪崩
- じいの天気予報：「明日は快晴」→ 次のカットで猛吹雪、じいだけ氷像
- ダイエット宣言：腹筋が1回もできず転がる → ご褒美にはちみつ一気食い

## チャンネル運用
- チャンネル名：Gonta & Piko（アイコンはゴンタの顔）
- 投稿：ショート週3本＋月1本の長尺（ショートをつないだ3〜5分のまとめ回）
- 投稿先：YouTubeショート・TikTok・Instagramリールに同じ動画
- 収益化の本命は長尺（ショートは集客）。2027年2月から収益化条件は「登録者1,000人＋8,000時間」または「ショート90日2,000万回」
- 量産型と見られないよう、台本は毎回オリジナルにし、キャラの関係やお約束を回をまたいで積み重ねる

## フォルダ構成（なければ作る）
```
characters/     キャラの設定画（顔アップ・全身）
episodes/<番号_名前>/
  storyboard.md   カット割り
  frames/         静止画カット
  clips/          動画カット
assets/se/  assets/bgm/
output/         完成動画と概要欄用クレジット
tools/          スクリプト類
```

## 作業の進め方
1. まずキャラ3匹の顔アップを作り、私の確認を取る（OKが出た画像を、以降すべての生成の参照画像にする）
2. 1本目の静止画カットを作る
3. 動画カットは5秒で試してから本番
4. 効果音・BGM・テロップを入れてつなぎ、1本完成させる
5. 手順をスクリプト化して、2本目からはカット割りを書くだけで作れるようにする
