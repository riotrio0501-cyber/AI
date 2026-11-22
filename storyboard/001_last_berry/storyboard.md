# 001「最後の木の実を守りたいだけなのに」カット割り表

- 長さ：約44秒（縦型 1080×1920）／セリフなし
- 流れ：**フリ**（c01）→ **失敗**（c02–c03）→ **さらに大失敗**（c04–c06）→ **オチ**（c07–c09）
- 食べ物は「どんぐり」ではなく **赤いベリーの房** に変更しています（既存作品の有名なギャグと重ならないように）

## ひと目でわかる流れ

| カット | 秒 | 何が起きるか | カメラ | 効果音 |
|---|---|---|---|---|
| c01 | 5 | 吹雪の中、ゴロが雪を掘ってベリーを発見。目がキラキラ | 寄り（正面） | 吹雪、キラーン |
| c02 | 5 | 食べようと口を開けた瞬間「ハ…ハ…ハックション！」ベリーが飛んで湖の氷の上をすべっていく | 寄り→ベリーを追って横に流れる | くしゃみ、ヒュッ、シャーッ |
| c03 | 6 | 追いかけたゴロがツルッと滑り、丸まってボールに。止まらず転がっていく | 引き（横から追いかける） | ツルッ、ビヨーン、ゴロゴロ |
| c04 | 3 | ドンさんが完成したてのダムを満足げにポンとたたく | 中くらい（ドンさん正面） | ポン |
| c05 | 5 | 転がってきたゴロが激突。ダムがバラバラに崩れる | 引き（ダム全体） | ドカーン、木がバキバキ |
| c06 | 3 | ドンさん、口あんぐり。小枝が耳からポロッと落ちる | 寄り（ドンさんの顔） | 間（無音）→ ポトッ |
| c07 | 6 | あふれた水が湖に流れこみ、一瞬で凍る。ゴロは氷の中でカチコチ。ベリーは目の前の氷の上 | 引き→ゴロに寄る | ザバーッ、ピキピキッ！ |
| c08 | 6 | ピピがよちよち登場。ベリーを拾って、パクッ。満足げ | 中くらい（ピピと氷のゴロ） | ペタペタ、パクッ、ゴクン |
| c09 | 5 | 氷の中のゴロのアップ。涙が一粒こぼれ、凍って落ちる「チーン」 | 超アップ（目） | BGM止まる → チーン |

## 生成・編集用データ（スクリプトが読みます）

- `duration`：完成動画で使う秒数／`gen_seconds`：生成する長さ（5か10）
- `se` の `at` は、そのカットの頭からの秒数
- `takes`：作り直した回数（生成のたびに記録）

```yaml
title: "最後の木の実を守りたいだけなのに"
slug: 001_last_berry
bgm:
  file: bgm/bouncy_pizzicato.wav
  volume: 0.32
  stop_at_cut: c09     # このカットの頭でBGMを止める（オチ前の「間」）
  fade_out: 0.15
telops:
  - text: "最後の木の実を\n守りたいだけなのに"
    start: 0.2
    end: 2.8
    position: top
cuts:
  - id: c01
    duration: 5
    gen_seconds: 5
    characters: [goro, berry]
    action_ja: "吹雪の中、ゴロが雪を掘ってベリーを発見。目がキラキラ"
    camera_ja: "寄り（正面）"
    frame: >-
      Goro is digging in a deep snowdrift during a gentle blizzard and has just uncovered the berry cluster,
      holding it up with both front paws, eyes sparkling with pure joy, mouth wide open in delight
    camera: "medium close-up, eye level, front view, snowflakes drifting in the foreground"
    motion: >-
      Goro lifts the berries above his head in triumph, wiggles his whole round body with happiness and wags his short tail fast,
      snow keeps falling, subtle camera push-in
    se:
      - {at: 0.0, file: se/wind_blizzard.wav, volume: 0.5}
      - {at: 1.6, file: se/sparkle.wav, volume: 0.8}
    takes: 0

  - id: c02
    duration: 5
    gen_seconds: 5
    characters: [goro, berry, lake]
    action_ja: "食べようとした瞬間にくしゃみ。ベリーが飛んで凍った湖の上をすべっていく"
    camera_ja: "寄り → ベリーを追って横に流れる"
    frame: >-
      Goro stands at the snowy edge of the frozen lake holding the berries right in front of his wide-open mouth,
      his nose twitching and face scrunched up just before a huge sneeze
    camera: "close-up, slightly low angle, frozen lake visible behind"
    motion: >-
      Goro sneezes explosively, his whole body squashes and stretches, the berries fly out of his paws,
      land on the ice and slide away fast across the glassy frozen lake, camera whip-pans to follow the sliding berries
    se:
      - {at: 0.3, file: se/sneeze_temp.wav, volume: 0.9}
      - {at: 1.5, file: se/whoosh.wav, volume: 0.7}
      - {at: 2.0, file: se/ice_slide.wav, volume: 0.6}
    takes: 0

  - id: c03
    duration: 6
    gen_seconds: 10
    characters: [goro, lake]
    action_ja: "追いかけたゴロがツルッと滑り、丸まってボールに。止まらず転がっていく"
    camera_ja: "引き（横から追いかける）"
    frame: >-
      Goro runs onto the glassy frozen lake chasing something out of frame, legs a blur,
      the first foot already slipping on the ice, a panicked expression
    camera: "wide shot, side view, tracking camera at ice level"
    motion: >-
      Goro slips, flips into the air, curls up into a perfect ball of caramel-orange shell and lands rolling,
      he rolls faster and faster across the ice unable to stop, ice spray behind him, camera tracks alongside
    se:
      - {at: 0.6, file: se/slip.wav, volume: 0.8}
      - {at: 1.1, file: se/boing.wav, volume: 0.7}
      - {at: 1.6, file: se/roll_rumble.wav, volume: 0.7}
    takes: 0

  - id: c04
    duration: 3
    gen_seconds: 5
    characters: [don, dam]
    action_ja: "ドンさんが完成したてのダムを満足げにポンとたたく"
    camera_ja: "中くらい（ドンさん正面）"
    frame: >-
      Don stands proudly in front of the freshly built dam, chest puffed out, patting the top log with one paw,
      eyes half-closed with quiet craftsman's pride
    camera: "medium shot, eye level, the dam fills the frame behind Don"
    motion: >-
      Don gives the dam two satisfied pats, nods slowly to himself, his tail thumps the snow once
    se:
      - {at: 0.5, file: se/pat.wav, volume: 0.8}
      - {at: 1.2, file: se/pat.wav, volume: 0.8}
    takes: 0

  - id: c05
    duration: 5
    gen_seconds: 5
    characters: [goro, don, dam]
    action_ja: "転がってきたゴロが激突。ダムがバラバラに崩れる"
    camera_ja: "引き（ダム全体）"
    frame: >-
      a wide view of the dam with Don standing next to it, while Goro, curled into a rolling caramel-orange ball,
      speeds toward the dam from the left across the ice
    camera: "wide shot, static camera, whole dam visible"
    motion: >-
      the rolling ball smashes into the center of the dam, logs and sticks burst outward in slow cartoon chaos,
      the dam collapses piece by piece, Don freezes in place with his paw still raised
    se:
      - {at: 0.9, file: se/crash.wav, volume: 1.0}
      - {at: 1.1, file: se/wood_crack.wav, volume: 0.8}
    takes: 0

  - id: c06
    duration: 3
    gen_seconds: 5
    characters: [don]
    action_ja: "ドンさん、口あんぐり。小枝が耳からポロッと落ちる"
    camera_ja: "寄り（ドンさんの顔）"
    frame: >-
      close-up of Don's face in total shock, jaw dropped, big orange teeth showing, bushy gray eyebrows raised high,
      scattered logs in the blurred background
    camera: "close-up, eye level, static"
    motion: >-
      Don stays completely frozen in shock, only his eye twitches once, then the twig slowly slips from behind his ear and falls
    se:
      - {at: 1.9, file: se/drop_tiny.wav, volume: 0.9}
    takes: 0

  - id: c07
    duration: 6
    gen_seconds: 10
    characters: [goro, berry, lake]
    action_ja: "あふれた水が一瞬で凍る。ゴロは氷の中でカチコチ。ベリーは目の前の氷の上"
    camera_ja: "引き → ゴロに寄る"
    frame: >-
      Goro, uncurled and dizzy, sits on the frozen lake as a wave of water from the broken dam rushes toward him,
      the berries resting on the ice just in front of him
    camera: "wide shot, low angle, then slow push-in toward Goro"
    motion: >-
      the wave washes over Goro and instantly freezes solid with a crackling frost effect, Goro is trapped inside a clear block of ice
      with a stunned face, the berries sit untouched on top of the ice right in front of his frozen eyes, camera pushes in
    se:
      - {at: 0.3, file: se/water_rush.wav, volume: 0.8}
      - {at: 1.8, file: se/freeze.wav, volume: 0.9}
    takes: 0

  - id: c08
    duration: 6
    gen_seconds: 10
    characters: [pipi, goro, berry]
    action_ja: "ピピがよちよち登場。ベリーを拾って、パクッ。満足げ"
    camera_ja: "中くらい（ピピと氷のゴロ）"
    frame: >-
      Pipi waddles into frame from the right toward the berries lying on the ice, right in front of Goro who is frozen inside a clear ice block
    camera: "medium shot, ice level, static"
    motion: >-
      Pipi waddles up, notices the berries, picks them up with a flipper, tosses them into its beak and swallows with a happy gulp,
      pats its full belly with a satisfied smile, completely ignoring the frozen Goro behind
    se:
      - {at: 0.0, file: se/waddle.wav, volume: 0.6}
      - {at: 3.0, file: se/pop.wav, volume: 0.8}
      - {at: 3.5, file: se/gulp.wav, volume: 0.9}
    takes: 0

  - id: c09
    duration: 5
    gen_seconds: 5
    characters: [goro]
    action_ja: "氷の中のゴロの目のアップ。涙が一粒こぼれ、凍って落ちる"
    camera_ja: "超アップ（目）"
    frame: >-
      extreme close-up of Goro's big emerald-green eye seen through clear ice, glossy and trembling, a single tear forming
    camera: "extreme close-up, static, very shallow depth of field"
    motion: >-
      a single tear rolls out of the eye, freezes into a tiny ice crystal and drops, sparkling, the eye stays sad and still
    se:
      - {at: 2.6, file: se/tink.wav, volume: 0.9}
    takes: 0
```
