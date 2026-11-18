"""ナレーション合成（ローカルTTS）

- voicevox : VOICEVOX CORE（推奨。声が自然。クレジット表記が必要）
- openjtalk: pyopenjtalk（pipだけで動く予備）
どちらも 48kHz mono float32 の numpy 配列を返す。
"""
import numpy as np

from . import config

SR = 48000
_engine = None


class OpenJTalkTTS:
    name = "openjtalk"
    credit = None

    def __init__(self):
        import pyopenjtalk
        from pyopenjtalk.htsengine import HTSEngine
        self.pj = pyopenjtalk
        v = config.OPENJTALK_VOICES[config.OPENJTALK_VOICE]
        path = v["path"] or pyopenjtalk.DEFAULT_HTS_VOICE
        self.engine = HTSEngine(path if isinstance(path, bytes) else str(path).encode())
        self.half_tone = v.get("half_tone", 0.0)
        self.speed_mul = v.get("speed_mul", 1.0)
        self.credit = v.get("credit")

    def synth(self, text, speed):
        e = self.engine
        e.set_speed(speed * self.speed_mul)
        e.add_half_tone(self.half_tone)
        x = np.asarray(e.synthesize(self.pj.extract_fullcontext(text)), np.float64)
        e.refresh()
        x = (x / 32768.0).astype(np.float32)
        return resample(x, e.get_sampling_frequency(), SR)


class SBV2TTS:
    """Style-Bert-VITS2（感情・抑揚が自然。torch CPUで動く）"""
    name = "sbv2"

    def __init__(self):
        from style_bert_vits2.constants import Languages
        from style_bert_vits2.logging import logger
        logger.remove()  # 進捗ログを出さない
        from style_bert_vits2.nlp import bert_models
        from style_bert_vits2.tts_model import TTSModel
        bert = str(config.SBV2_DIR / "bert" / "deberta-v2-large-japanese-char-wwm")
        bert_models.load_model(Languages.JP, bert).float()  # 新しいtransformersはfp16のまま読むため
        bert_models.load_tokenizer(Languages.JP, bert)
        v = config.SBV2_VOICES[config.SBV2_VOICE]
        d = config.SBV2_DIR / "models" / v["dir"]
        self.model = TTSModel(model_path=next(d.glob("*.safetensors")), config_path=d / "config.json",
                              style_vec_path=d / "style_vectors.npy", device="cpu")
        self.v = v
        self.credit = v["credit"]

    def synth(self, text, speed):
        v = self.v
        sr, x = self.model.infer(text=text, style=v.get("style", "Neutral"), style_weight=v.get("style_weight", 1.0),
                                 length=1.0 / (speed * v.get("speed_mul", 1.0)), sdp_ratio=v.get("sdp_ratio", 0.3),
                                 pitch_scale=v.get("pitch", 1.0), intonation_scale=v.get("intonation", 1.1))
        x = np.asarray(x, np.float32)
        if np.abs(x).max() > 2:
            x /= 32768.0
        return resample(x, sr, SR)


class VoicevoxTTS:
    name = "voicevox"
    credit = config.VOICEVOX_CREDIT

    def __init__(self):
        from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
        d = config.VOICEVOX_DIR
        lib = next((d / "voicevox_onnxruntime-linux-x64-1.17.3" / "lib").glob("libvoicevox_onnxruntime.so.*"))
        ort = Onnxruntime.load_once(filename=str(lib))
        self.syn = Synthesizer(ort, OpenJtalk(str(d / "open_jtalk_dic_utf_8-1.11")))
        sid = config.VOICEVOX_STYLE_ID
        for p in sorted((d / "vvm_repo" / "vvms").glob("*.vvm")):
            with VoiceModelFile.open(p) as m:
                if any(st.id == sid for c in m.metas for st in c.styles):
                    self.syn.load_voice_model(m)
                    break
        self.sid = sid

    def synth(self, text, speed):
        q = self.syn.create_audio_query(text, self.sid)
        q.speed_scale = speed
        q.pre_phoneme_length = 0.05
        q.post_phoneme_length = 0.05
        q.output_sampling_rate = SR
        import io, wave
        with wave.open(io.BytesIO(self.syn.synthesis(q, self.sid))) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        return x


def resample(x, sr, to):
    if sr == to:
        return x
    n = int(len(x) * to / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def get_engine():
    global _engine
    if _engine:
        return _engine
    want = config.TTS_BACKEND
    if want == "sbv2":
        _engine = SBV2TTS()
        return _engine
    if want in ("auto", "voicevox"):
        try:
            _engine = VoicevoxTTS()
            return _engine
        except Exception as e:  # noqa: BLE001
            if want == "voicevox":
                raise
            print(f"  [TTS] VOICEVOXが使えないため OpenJTalk を使用（{type(e).__name__}: {e}）")
    _engine = OpenJTalkTTS()
    return _engine


def trim_silence(x, thresh=0.01, pad=0.03):
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(x), idx[-1] + int(pad * SR))
    return x[a:b]


def synth(text, speed=None):
    eng = get_engine()
    x = trim_silence(eng.synth(text, speed or config.TTS_SPEED))
    peak = np.max(np.abs(x)) or 1.0
    return x / peak * 0.85
