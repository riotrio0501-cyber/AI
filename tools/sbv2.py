"""Style-Bert-VITS2（感情つきの声）をこの作業環境の中で動かす。
モデルは初回に Hugging Face から ~/models/sbv2 に自動ダウンロード。
声: JVNV（CC BY-SA 4.0、商用可・クレジット表記が必要）
感情(style): Neutral / Angry / Disgust / Fear / Happy / Sad / Surprise
"""
from pathlib import Path
import numpy as np

M = Path.home() / "models" / "sbv2"
_bert = False
_models = {}

# 台本で使える日本語の感情名 → モデルの感情名
EMOTIONS = {"ふつう": "Neutral", "怒り": "Angry", "嫌悪": "Disgust", "おびえ": "Fear", "喜び": "Happy",
            "悲しみ": "Sad", "驚き": "Surprise"}


def ensure():
    from huggingface_hub import snapshot_download
    if not (M / "jvnv").exists():
        snapshot_download("litagin/style_bert_vits2_jvnv", local_dir=str(M / "jvnv"), allow_patterns=["jvnv-*-jp/*"])
    b = M / "bert" / "deberta-v2-large-japanese-char-wwm"
    if not (b / "pytorch_model.bin").exists():
        snapshot_download("ku-nlp/deberta-v2-large-japanese-char-wwm", local_dir=str(b),
                          allow_patterns=["config.json", "pytorch_model.bin", "special_tokens_map.json",
                                          "tokenizer_config.json", "vocab.txt"])


def _load(name):
    global _bert
    from style_bert_vits2.constants import Languages
    from style_bert_vits2.logging import logger
    from style_bert_vits2.nlp import bert_models
    from style_bert_vits2.tts_model import TTSModel
    if not _bert:
        ensure(); logger.remove()
        b = str(M / "bert" / "deberta-v2-large-japanese-char-wwm")
        bert_models.load_model(Languages.JP, b).float()
        bert_models.load_tokenizer(Languages.JP, b)
        _bert = True
    if name not in _models:
        d = M / "jvnv" / name if (M / "jvnv" / name).exists() else M / "extra" / name
        _models[name] = TTSModel(model_path=next(d.glob("*.safetensors")), config_path=d / "config.json",
                                 style_vec_path=d / "style_vectors.npy", device="cpu")
    return _models[name]


def synth(text, model, emotion="Neutral", strength=2.0, speed=1.0, volume=1.0, intonation=1.2):
    """(sr, float32 配列) を返す"""
    emotion = EMOTIONS.get(emotion, emotion)
    sr, x = _load(model).infer(text=text, style=emotion, style_weight=strength if emotion != "Neutral" else 1.0,
                               sdp_ratio=0.4, length=1.0 / speed, intonation_scale=intonation)
    x = np.asarray(x, np.float32)
    if np.abs(x).max() > 2:
        x /= 32768.0
    return sr, x * volume
