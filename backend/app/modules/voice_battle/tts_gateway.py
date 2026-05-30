from __future__ import annotations

import base64
import io
import os
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

try:
    import sherpa_onnx
except ImportError:  # pragma: no cover
    sherpa_onnx = None  # type: ignore[assignment]


@dataclass(slots=True)
class SherpaOnnxTtsConfig:
    model_type: str = "vits"
    provider: str = "cpu"
    num_threads: int = 1
    debug: bool = False
    rule_fsts: str = ""
    max_num_sentences: int = 1
    vits_model: str = ""
    vits_lexicon: str = ""
    vits_tokens: str = ""
    vits_data_dir: str = ""


_tts: Any | None = None
_tts_lock = threading.Lock()


def _load_config_from_env() -> SherpaOnnxTtsConfig:
    model_type = os.getenv("SHERPA_ONNX_TTS_MODEL_TYPE", "vits").strip().lower() or "vits"
    model_dir = os.getenv("SHERPA_ONNX_TTS_MODEL_DIR", "").strip()
    vits_model = os.getenv("SHERPA_ONNX_TTS_VITS_MODEL", "").strip()
    vits_tokens = os.getenv("SHERPA_ONNX_TTS_VITS_TOKENS", "").strip()
    vits_lexicon = os.getenv("SHERPA_ONNX_TTS_VITS_LEXICON", "").strip()
    vits_data_dir = os.getenv("SHERPA_ONNX_TTS_VITS_DATA_DIR", "").strip()
    rule_fsts = os.getenv("SHERPA_ONNX_TTS_RULE_FSTS", "").strip()

    if model_dir:
        base = Path(model_dir)
        if not vits_tokens:
            token_file = base / "tokens.txt"
            if token_file.exists():
                vits_tokens = str(token_file)
        if not vits_lexicon:
            lex_file = base / "lexicon.txt"
            if lex_file.exists():
                vits_lexicon = str(lex_file)
        if not vits_model:
            for name in ("model.int8.onnx", "model.onnx"):
                candidate = base / name
                if candidate.exists():
                    vits_model = str(candidate)
                    break
        if not rule_fsts:
            candidates = [base / "phone.fst", base / "date.fst", base / "number.fst"]
            if all(p.exists() for p in candidates):
                rule_fsts = ",".join(str(p) for p in candidates)

    provider = os.getenv("SHERPA_ONNX_TTS_PROVIDER", "cpu").strip().lower() or "cpu"
    num_threads = int(os.getenv("SHERPA_ONNX_TTS_NUM_THREADS", "1"))
    debug = os.getenv("SHERPA_ONNX_TTS_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}
    max_num_sentences = int(os.getenv("SHERPA_ONNX_TTS_MAX_NUM_SENTENCES", "1"))

    cfg = SherpaOnnxTtsConfig(
        model_type=model_type,
        provider=provider,
        num_threads=num_threads,
        debug=debug,
        rule_fsts=rule_fsts,
        max_num_sentences=max_num_sentences,
        vits_model=vits_model,
        vits_lexicon=vits_lexicon,
        vits_tokens=vits_tokens,
        vits_data_dir=vits_data_dir,
    )

    if cfg.model_type != "vits":
        raise ValueError("Unsupported SHERPA_ONNX_TTS_MODEL_TYPE. Supported: vits.")
    if not cfg.vits_model:
        raise ValueError(
            "Missing sherpa-onnx TTS config. Require env: "
            "`SHERPA_ONNX_TTS_MODEL_DIR` (contains tokens.txt + model.onnx/model.int8.onnx) "
            "or `SHERPA_ONNX_TTS_VITS_MODEL`."
        )
    if not cfg.vits_data_dir and not cfg.vits_tokens:
        raise ValueError(
            "Missing sherpa-onnx TTS config. Require env: "
            "`SHERPA_ONNX_TTS_VITS_DATA_DIR` or `SHERPA_ONNX_TTS_VITS_TOKENS`."
        )

    return cfg


def _get_tts() -> Any:
    global _tts
    if _tts is not None:
        return _tts
    with _tts_lock:
        if _tts is not None:
            return _tts
        if sherpa_onnx is None or np is None:
            raise RuntimeError("Missing dependencies for TTS. Please install `sherpa-onnx` and `numpy`.")

        cfg = _load_config_from_env()
        tts_config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=cfg.vits_model,
                    lexicon=cfg.vits_lexicon,
                    tokens=cfg.vits_tokens,
                    data_dir=cfg.vits_data_dir,
                ),
                provider=cfg.provider,
                debug=cfg.debug,
                num_threads=cfg.num_threads,
            ),
            rule_fsts=cfg.rule_fsts,
            max_num_sentences=cfg.max_num_sentences,
        )
        if not tts_config.validate():
            raise ValueError("Invalid sherpa-onnx TTS config.")
        _tts = sherpa_onnx.OfflineTts(tts_config)
        return _tts


def synthesize_wav_bytes(text: str) -> tuple[bytes, int]:
    content = (text or "").strip()
    if not content:
        return b"", 0
    if np is None:
        raise RuntimeError("Missing dependency `numpy`.")

    tts = _get_tts()
    gen_config = sherpa_onnx.GenerationConfig()
    gen_config.sid = int(os.getenv("SHERPA_ONNX_TTS_SID", "0"))
    gen_config.speed = float(os.getenv("SHERPA_ONNX_TTS_SPEED", "1.0"))
    gen_config.silence_scale = float(os.getenv("SHERPA_ONNX_TTS_SILENCE_SCALE", "0.2"))

    audio = tts.generate(content, gen_config)
    samples = audio.samples
    if len(samples) == 0:
        return b"", 0

    float_samples = np.asarray(samples, dtype=np.float32)
    int16_samples = np.clip(float_samples, -1.0, 1.0)
    int16_samples = (int16_samples * 32767.0).astype(np.int16)

    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(int(audio.sample_rate))
            wf.writeframes(int16_samples.tobytes())
        return buffer.getvalue(), int(audio.sample_rate)


def synthesize_wav_base64(text: str) -> dict[str, Any]:
    wav_bytes, sample_rate = synthesize_wav_bytes(text)
    if not wav_bytes:
        return {"audio_b64": "", "sample_rate": 0, "mime_type": "audio/wav"}
    return {
        "audio_b64": base64.b64encode(wav_bytes).decode("ascii"),
        "sample_rate": sample_rate,
        "mime_type": "audio/wav",
    }

