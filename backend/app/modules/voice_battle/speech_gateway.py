from __future__ import annotations

import os
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.shared_types.game_types import VoiceTurnPayload

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

try:
    import sherpa_onnx
except ImportError:  # pragma: no cover
    sherpa_onnx = None  # type: ignore[assignment]


@dataclass(slots=True)
class SherpaOnnxAsrConfig:
    model_type: str = "paraformer"
    tokens: str = ""
    paraformer: str = ""
    encoder: str = ""
    decoder: str = ""
    joiner: str = ""
    provider: str = "cpu"
    num_threads: int = 1
    decoding_method: str = "greedy_search"
    max_active_paths: int = 4


_recognizer: Any | None = None
_recognizer_lock = threading.Lock()


def _load_config_from_env() -> SherpaOnnxAsrConfig:
    model_type = os.getenv("SHERPA_ONNX_MODEL_TYPE", "paraformer").strip().lower() or "paraformer"
    model_dir = os.getenv("SHERPA_ONNX_MODEL_DIR", "").strip()
    tokens = os.getenv("SHERPA_ONNX_TOKENS", "").strip()
    paraformer = os.getenv("SHERPA_ONNX_PARAFORMER", "").strip()
    encoder = os.getenv("SHERPA_ONNX_ENCODER", "").strip()
    decoder = os.getenv("SHERPA_ONNX_DECODER", "").strip()
    joiner = os.getenv("SHERPA_ONNX_JOINER", "").strip()

    if model_dir:
        base = Path(model_dir)
        if not tokens:
            token_file = base / "tokens.txt"
            if token_file.exists():
                tokens = str(token_file)
        if model_type == "paraformer" and not paraformer:
            for name in ("model.int8.onnx", "model.onnx"):
                candidate = base / name
                if candidate.exists():
                    paraformer = str(candidate)
                    break

    provider = os.getenv("SHERPA_ONNX_PROVIDER", "cpu").strip().lower() or "cpu"
    num_threads = int(os.getenv("SHERPA_ONNX_NUM_THREADS", "1"))
    decoding_method = os.getenv("SHERPA_ONNX_DECODING_METHOD", "greedy_search").strip() or "greedy_search"
    max_active_paths = int(os.getenv("SHERPA_ONNX_MAX_ACTIVE_PATHS", "4"))

    cfg = SherpaOnnxAsrConfig(
        model_type=model_type,
        tokens=tokens,
        paraformer=paraformer,
        encoder=encoder,
        decoder=decoder,
        joiner=joiner,
        provider=provider,
        num_threads=num_threads,
        decoding_method=decoding_method,
        max_active_paths=max_active_paths,
    )

    if cfg.model_type == "paraformer":
        if not cfg.tokens or not cfg.paraformer:
            raise ValueError(
                "Missing sherpa-onnx config for paraformer. Require env: "
                "`SHERPA_ONNX_MODEL_DIR` (contains tokens.txt + model.onnx/model.int8.onnx) "
                "or (`SHERPA_ONNX_TOKENS` + `SHERPA_ONNX_PARAFORMER`)."
            )
    elif cfg.model_type == "transducer":
        if not cfg.tokens or not cfg.encoder or not cfg.decoder or not cfg.joiner:
            raise ValueError(
                "Missing sherpa-onnx config for transducer. Require env: "
                "`SHERPA_ONNX_TOKENS`, `SHERPA_ONNX_ENCODER`, `SHERPA_ONNX_DECODER`, `SHERPA_ONNX_JOINER`."
            )
    else:
        raise ValueError("Unsupported SHERPA_ONNX_MODEL_TYPE. Supported: paraformer, transducer.")

    return cfg


def _get_recognizer() -> Any:
    global _recognizer
    if _recognizer is not None:
        return _recognizer
    with _recognizer_lock:
        if _recognizer is not None:
            return _recognizer
        if sherpa_onnx is None or np is None:
            raise RuntimeError("Missing dependencies for ASR. Please install `sherpa-onnx` and `numpy`.")

        cfg = _load_config_from_env()
        if cfg.model_type == "paraformer":
            _recognizer = sherpa_onnx.OfflineRecognizer.from_paraformer(
                paraformer=cfg.paraformer,
                tokens=cfg.tokens,
                num_threads=cfg.num_threads,
                decoding_method=cfg.decoding_method,
                provider=cfg.provider,
            )
        else:
            _recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
                encoder=cfg.encoder,
                decoder=cfg.decoder,
                joiner=cfg.joiner,
                tokens=cfg.tokens,
                num_threads=cfg.num_threads,
                decoding_method=cfg.decoding_method,
                max_active_paths=cfg.max_active_paths,
                provider=cfg.provider,
            )
        return _recognizer


def _read_wave(wave_filename: str) -> tuple[Any, int]:
    if np is None:
        raise RuntimeError("Missing dependency `numpy`.")
    with wave.open(wave_filename) as f:
        if f.getnchannels() != 1:
            raise ValueError(f"Only mono wav is supported. channels={f.getnchannels()}")
        if f.getsampwidth() != 2:
            raise ValueError(f"Only 16-bit PCM wav is supported. sampwidth={f.getsampwidth()}")
        num_samples = f.getnframes()
        samples = f.readframes(num_samples)
        samples_int16 = np.frombuffer(samples, dtype=np.int16)
        samples_float32 = samples_int16.astype(np.float32) / 32768
        return samples_float32, f.getframerate()


def transcribe_audio(audio_payload: VoiceTurnPayload) -> dict:
    """
    输入:
    - audio_payload.audio_path: 音频文件路径
    - audio_payload.input_mode: 输入来源(默认 voice)

    输出:
    - {"transcript": str, "confidence": float}

    示例:
    - 输入 {"audio_path":"./demo.wav"} -> 输出 {"transcript":"我想确认薪资区间","confidence":0.9}
    """
    audio_path = str(audio_payload.audio_path).strip()
    if not audio_path:
        return {"transcript": "", "confidence": 0.0}

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"audio file not found: {audio_path}")

    recognizer = _get_recognizer()
    samples, sample_rate = _read_wave(audio_path)

    stream = recognizer.create_stream()
    stream.accept_waveform(sample_rate, samples)
    recognizer.decode_stream(stream)
    transcript = str(stream.result.text).strip()

    default_conf = float(os.getenv("SHERPA_ONNX_DEFAULT_CONFIDENCE", "0.9"))
    confidence = default_conf if transcript else 0.0
    return {"transcript": transcript, "confidence": confidence}
