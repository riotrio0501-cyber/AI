# キャラクター設定（固定）

このファイルの ```prompt:〜``` ブロックは、画像・動画生成のプロンプトに **一字一句そのまま** 入ります
（`tools/prompts.py` が自動で差し込みます）。見た目を変えたいときは、ここだけを直してください。

> オリジナル性のルール
> - 作品名・キャラ名・スタジオ名・「〜風」はプロンプトに書かない
> - 既存の有名キャラと似ないよう、色・体型・目じるしをはっきり決めている
> - 食べ物は「どんぐり」ではなく **赤いベリーの房（ゆきベリー）** にしている

---

## 共通：絵のタッチ

```prompt:style
3D animated feature film still, stylized CG cartoon, soft rounded shapes, soft fluffy fur and feathers with subsurface scattering, big glossy expressive eyes, exaggerated squash-and-stretch facial expressions, prehistoric frozen world of snow and blue ice, soft cinematic lighting with cool blue shadows and warm golden highlights, shallow depth of field, vertical 9:16 composition, family-friendly slapstick comedy, highly detailed
```

## 共通：入れてほしくないもの（ネガティブ）

```prompt:negative
text, letters, subtitles, logo, watermark, signature, humans, extra limbs, extra fingers, extra eyes, deformed face, photorealistic, squirrel, sloth, mammoth, saber-toothed cat, acorn, clothing
```

---

## ゴロ（主人公）

- 古代のアルマジロの仲間。ほぼ完全な球体で、ひざ下くらいの小ささ
- 甲羅：あたたかいキャラメルオレンジ。丸い六角形のもようが濃い茶色でふち取りされている
- お腹と顔：クリーム色でふわふわ
- 目：とても大きい エメラルドグリーン
- **目じるし：甲羅の左上が小さく欠けている**（ブレ確認ポイント）
- 性格：食いしん坊。うれしいとしっぽをぶんぶん振る。丸まるとボールになって止まれない

```prompt:goro
Goro, a small round prehistoric armadillo-like creature shaped almost like a perfect ball, knee-high, a heavy dome shell in warm caramel orange covered with rounded hexagon plates outlined in dark chocolate brown, a small chip missing from the top-left edge of the shell, soft cream-colored fuzzy face and belly, chubby cheeks, very large glossy emerald-green eyes, a tiny pink nose, small rounded ears, short stubby legs, a short thick tail with a round knob at the tip
```

## ピピ（ちびペンギン）

- 卵型のちびペンギン。ゴロより少し小さい
- 背中とつばさ：つるっとした スレートブルー（灰色がかった青）。ふわふわの灰色ヒナではない
- お腹：まっ白。ほっぺ：オレンジ寄りの黄色
- 目：大きい はちみつ色（アンバー）
- **目じるし：頭のてっぺんに くるんと巻いた羽が1本**
- 性格：しっかり者のつもり。マイペースで、悪気なくおいしいところを持っていく

```prompt:pipi
Pipi, a tiny egg-shaped penguin chick slightly smaller than Goro, smooth sleek slate-blue back and flippers (not fluffy gray down), a bright white belly, round orange-yellow cheek patches, a short orange beak, big round honey-amber eyes, a single curly feather tuft curling up from the top of the head, small orange webbed feet
```

## ドンさん（巨大ビーバーの職人）

- 古代の巨大ビーバー。ゴロの3倍くらいの背の高さ、洋なし型のどっしり体型
- 毛：こげ茶（ダークチョコレート色）、鼻まわりは明るい黄土色
- まゆ毛：太くてもじゃもじゃの **灰色**
- 歯：四角くて大きいオレンジ色の前歯2本
- 目：小さめで真剣な こげ茶
- しっぽ：平たいオール型、こうし模様
- **目じるし：右耳のうしろに小枝を1本はさんでいる**（職人のえんぴつ代わり）
- 性格：まじめな職人。作ったものを毎回こわされ、言葉を失う

```prompt:don
Don, a giant prehistoric beaver about three times taller than Goro, heavy pear-shaped body, thick dark chocolate-brown fur, a lighter tan muzzle, very thick bushy gray eyebrows, two large squared orange front teeth, small serious dark-brown eyes, a broad flat paddle tail with a crosshatch texture, a short twig tucked behind the right ear like a carpenter's pencil
```

---

## 小道具・舞台

```prompt:berry
a single plump cluster of three glossy bright-red berries on a tiny twig with one green leaf, dusted with frost
```

```prompt:lake
a wide frozen lake of smooth glassy blue ice surrounded by snowy hills and frosted pine trees
```

```prompt:dam
a neat, freshly built beaver dam of stacked logs and sticks packed with mud across a narrow stream at the edge of the frozen lake
```

---

## 設定画（キャラシート）で作るもの

各キャラについて以下を作り、`assets/characters/` に保存します。
- 正面 / 横 / 後ろ（3面図、白背景）
- 表情差分：うれしい・びっくり・がっかり・必死
- ブレ確認のチェック項目：**色、目の色、体型、目じるし**（ゴロ＝甲羅の欠け／ピピ＝頭の巻き羽／ドンさん＝耳の小枝）
