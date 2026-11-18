"""ブランド設定・動画仕様（ここを変えれば全動画に反映される）"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 動画仕様
W, H, FPS = 1080, 1920, 30

# ブランド
ACCOUNT_NAME = "知らなきゃ損ラボ"
ACCOUNT_ID = "@shiranakya_son_lab"
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
TTS_BACKEND = "openjtalk"  # openjtalk / voicevox / auto（voicevox→だめならopenjtalk）
TTS_SPEED = 1.22      # 速め
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
