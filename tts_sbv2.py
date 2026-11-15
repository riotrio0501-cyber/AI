"""Style-Bert-VITS2 による日本語TTS（ローカル実行・CPU）。

声モデルは Hugging Face から初回だけダウンロードして models/ にキャッシュする。
series.yaml の voice セクションで声を選ぶ:

    voice:
      engine: sbv2                # sbv2 / openjtalk
      model: koharune-ami         # VOICES のキー
      style: Neutral
      style_weight: 1.0
      speed: 1.0                  # 1.0 が標準。大きいほど速い
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models"

# key: (HF repo, サブフォルダ, クレジット表記)
VOICES = {
    "koharune-ami": ("litagin/sbv2_koharune_ami", "koharune-ami",
                     "音声: Style-Bert-VITS2モデル 小春音アミ、あみたろの声素材工房 (https://amitaro.net/)"),
    "jvnv-F1-jp": ("litagin/style_bert_vits2_jvnv", "jvnv-F1-jp",
                   "音声: Style-Bert-VITS2 JVNVモデル (CC BY-SA 4.0)"),
    "jvnv-F2-jp": ("litagin/style_bert_vits2_jvnv", "jvnv-F2-jp",
                   "音声: Style-Bert-VITS2 JVNVモデル (CC BY-SA 4.0)"),
    "jvnv-M1-jp": ("litagin/style_bert_vits2_jvnv", "jvnv-M1-jp",
                   "音声: Style-Bert-VITS2 JVNVモデル (CC BY-SA 4.0)"),
    "jvnv-M2-jp": ("litagin/style_bert_vits2_jvnv", "jvnv-M2-jp",
                   "音声: Style-Bert-VITS2 JVNVモデル (CC BY-SA 4.0)"),
}

_models: dict = {}
_bert_loaded = False


def _load(key: str):
    global _bert_loaded
    from huggingface_hub import hf_hub_download, list_repo_files
    from style_bert_vits2.constants import Languages
    from style_bert_vits2.nlp import bert_models
    from style_bert_vits2.tts_model import TTSModel

    if not _bert_loaded:
        name = "ku-nlp/deberta-v2-large-japanese-char-wwm"
        # 新しい transformers は fp16 のまま読むので CPU 推論用に fp32 へ
        bert_models.load_model(Languages.JP, name).float()
        bert_models.load_tokenizer(Languages.JP, name)
        _bert_loaded = True
    if key not in _models:
        repo, sub, _ = VOICES[key]
        files = [f for f in list_repo_files(repo) if f.startswith(sub + "/")]
        paths = {Path(f).name: hf_hub_download(repo, f, local_dir=MODEL_DIR) for f in files}
        st = next(p for n, p in paths.items() if n.endswith(".safetensors"))
        _models[key] = TTSModel(model_path=Path(st), config_path=Path(paths["config.json"]),
                                style_vec_path=Path(paths["style_vectors.npy"]), device="cpu")
    return _models[key]


def credit(key: str) -> str:
    return VOICES[key][2]


def tts(text: str, model: str = "koharune-ami", style: str = "Neutral",
        style_weight: float = 1.0, speed: float = 1.0, sdp_ratio: float = 0.25) -> tuple[np.ndarray, int]:
    m = _load(model)
    if style not in m.style2id:
        style = "Neutral"
    import torch
    torch.manual_seed(0)  # 毎回同じ読み方になるよう固定
    sr, audio = m.infer(text=text, style=style, style_weight=style_weight,
                        length=1.0 / speed, sdp_ratio=sdp_ratio, split_interval=0.25)
    return audio.astype(np.float32) / 32768.0, sr
