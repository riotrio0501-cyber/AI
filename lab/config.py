"""ブランド設定・動画仕様（ここを変えれば全動画に反映される）"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 動画仕様
W, H, FPS = 1080, 1920, 30

# ブランド
ACCOUNT_NAME = "知らなきゃ損ラボ"
ACCOUNT_ID = "@shiranakya_son_lab"
PROFILE_IMAGE = ROOT / "assets" / "profile.png"  # プロフィール画像（フォローボタン・左上に使用）
NAVY = (0x13, 0x29, 0x4B)
GREEN = (0x2B, 0xAE, 0x74)
GOLD = (0xF5, 0xB8, 0x3D)
WHITE = (255, 255, 255)

# 長さの規定（秒）
LENGTH_RULES = {
    "short": {"min": 20, "max": 40, "points": 1},
    "long": {"min": 60, "max": 75, "points": 3},
}

# 対象タグ
TARGETS = ["学生・若者", "新社会人", "一人暮らし", "30〜40代", "季節"]

# フォント（Noto Sans CJK JP。apt: fonts-noto-cjk fonts-noto-cjk-extra）
FONT_BLACK = ("/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", 0)
FONT_BOLD = ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0)

# TikTokのUIに隠れにくい領域（上下・右端を避ける）
SAFE_TOP = 150
SAFE_BOTTOM = 1920 - 420
SAFE_SIDE = 80

# ナレーション
TTS_BACKEND = "sbv2"  # sbv2（自然・推奨） / openjtalk（軽量） / voicevox / auto
TTS_SPEED = 1.22      # 速め
# OpenJTalkの声（htsvoice）。tohoku-f01 は CC BY 4.0 なのでクレジットを自動でキャプションに入れる
HTSVOICE_DIR = ROOT / "models" / "htsvoice_tohoku"
OPENJTALK_VOICE = "mei"
OPENJTALK_VOICES = {
    "mei": {"path": None, "half_tone": 1.0},
    "mei_high": {"path": None, "half_tone": 2.5},
    "tohoku_neutral": {"path": HTSVOICE_DIR / "tohoku-f01-neutral.htsvoice", "speed_mul": 0.95,
                       "credit": "音声: HTS voice tohoku-f01 (CC BY 4.0)"},
    "tohoku_happy": {"path": HTSVOICE_DIR / "tohoku-f01-happy.htsvoice", "speed_mul": 0.95,
                     "credit": "音声: HTS voice tohoku-f01 (CC BY 4.0)"},
}
# Style-Bert-VITS2（いちばん人間らしい。モデルは Hugging Face から取得）
SBV2_DIR = ROOT / "models" / "sbv2"
SBV2_VOICE = "koharune_ami"
_AMI = "あみたろの声素材工房 (https://amitaro.net/)"
SBV2_VOICES = {
    "koharune_ami": {"dir": "koharune-ami", "style": "Neutral", "speed_mul": 1.0,
                     "credit": f"Style-Bert-VITS2モデル: 小春音アミ、{_AMI}"},
    "koharune_ami_runrun": {"dir": "koharune-ami", "style": "るんるん", "speed_mul": 1.0,
                            "credit": f"Style-Bert-VITS2モデル: 小春音アミ、{_AMI}"},
    "amitaro": {"dir": "amitaro", "style": "Neutral", "speed_mul": 1.0,
                "credit": f"Style-Bert-VITS2モデル: あみたろ、{_AMI}"},
    "jvnv_f1": {"dir": "jvnv-F1-jp", "style": "Neutral", "speed_mul": 1.0,
                "credit": "Style-Bert-VITS2モデル: jvnv-F1-jp (JVNV corpus, CC BY-SA 4.0)"},
}
VOICEVOX_DIR = Path("/home/user/tools/voicevox")
VOICEVOX_STYLE_ID = 8  # 春日部つむぎ（ノーマル）
VOICEVOX_CREDIT = "VOICEVOX:春日部つむぎ"
SCENE_GAP = 0.12       # シーン間の無音（秒）
TAIL = 0.8             # 最後の余韻（秒）

# 音量
BGM_GAIN_DB = -24
SFX_GAIN_DB = -18

# 断定しすぎ・金融商品の推奨を検出するためのNGワード（警告のみ）
NG_WORDS = ["必ず得", "絶対", "100%", "確実に", "NISA", "iDeCo", "投資信託", "株を買", "保険に入",
            "クレジットカードを作", "おすすめのカード", "おすすめの保険"]
