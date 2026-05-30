from __future__ import annotations

import logging
import os
import tempfile
import threading
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.modules.voice_battle.audio_convert import AudioConvertError, ensure_mono_wav
from app.shared_types.game_types import VoiceTurnPayload

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]

try:
    import sherpa_onnx
except ImportError:  # pragma: no cover
    sherpa_onnx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class AsrPipelineError(RuntimeError):
    """ASR 配置、转码或解码失败。"""


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


def sherpa_onnx_installed() -> bool:
    return sherpa_onnx is not None and np is not None


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
            raise AsrPipelineError(
                "Missing sherpa-onnx config for paraformer. Require env: "
                "`SHERPA_ONNX_MODEL_DIR` (contains tokens.txt + model.onnx/model.int8.onnx) "
                "or (`SHERPA_ONNX_TOKENS` + `SHERPA_ONNX_PARAFORMER`)."
            )
    elif cfg.model_type == "transducer":
        if not cfg.tokens or not cfg.encoder or not cfg.decoder or not cfg.joiner:
            raise AsrPipelineError(
                "Missing sherpa-onnx config for transducer. Require env: "
                "`SHERPA_ONNX_TOKENS`, `SHERPA_ONNX_ENCODER`, `SHERPA_ONNX_DECODER`, `SHERPA_ONNX_JOINER`."
            )
    else:
        raise AsrPipelineError("Unsupported SHERPA_ONNX_MODEL_TYPE. Supported: paraformer, transducer.")

    return cfg


def get_asr_config_summary() -> dict[str, Any]:
    model_dir = os.getenv("SHERPA_ONNX_MODEL_DIR", "").strip()
    model_type = os.getenv("SHERPA_ONNX_MODEL_TYPE", "paraformer").strip().lower() or "paraformer"
    tokens = os.getenv("SHERPA_ONNX_TOKENS", "").strip()
    paraformer = os.getenv("SHERPA_ONNX_PARAFORMER", "").strip()

    if model_dir:
        base = Path(model_dir)
        if not tokens and (base / "tokens.txt").exists():
            tokens = str(base / "tokens.txt")
        if model_type == "paraformer" and not paraformer:
            for name in ("model.int8.onnx", "model.onnx"):
                candidate = base / name
                if candidate.exists():
                    paraformer = str(candidate)
                    break

    files_ok = bool(tokens and Path(tokens).exists())
    if model_type == "paraformer":
        files_ok = files_ok and bool(paraformer and Path(paraformer).exists())

    return {
        "type": model_type,
        "dir": model_dir or None,
        "tokens": tokens or None,
        "paraformer": paraformer or None,
        "files_ok": files_ok,
    }


def probe_asr_load() -> tuple[bool, str]:
    try:
        _get_recognizer()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _find_sample_wav() -> Path | None:
    model_dir = os.getenv("SHERPA_ONNX_MODEL_DIR", "").strip()
    if not model_dir:
        return None
    test_dir = Path(model_dir) / "test_wavs"
    if not test_dir.exists():
        return None
    for name in ("0.wav", "1.wav", "2.wav"):
        candidate = test_dir / name
        if candidate.exists():
            return candidate
    wavs = sorted(test_dir.glob("*.wav"))
    return wavs[0] if wavs else None


def probe_sample_transcript() -> tuple[str, str]:
    sample = _find_sample_wav()
    if sample is None:
        return "", "No test_wavs sample found under SHERPA_ONNX_MODEL_DIR."
    try:
        result = transcribe_file(sample, mime_type="audio/wav")
        return str(result.get("transcript", "")), ""
    except Exception as exc:
        return "", str(exc)


def _get_recognizer() -> Any:
    global _recognizer
    if _recognizer is not None:
        return _recognizer
    with _recognizer_lock:
        if _recognizer is not None:
            return _recognizer
        if sherpa_onnx is None or np is None:
            raise AsrPipelineError("Missing dependencies for ASR. Please install `sherpa-onnx` and `numpy`.")

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
        raise AsrPipelineError("Missing dependency `numpy`.")
    with wave.open(wave_filename) as f:
        if f.getnchannels() != 1:
            raise AsrPipelineError(f"Only mono wav is supported. channels={f.getnchannels()}")
        if f.getsampwidth() != 2:
            raise AsrPipelineError(f"Only 16-bit PCM wav is supported. sampwidth={f.getsampwidth()}")
        num_samples = f.getnframes()
        samples = f.readframes(num_samples)
        samples_int16 = np.frombuffer(samples, dtype=np.int16)
        samples_float32 = samples_int16.astype(np.float32) / 32768
        return samples_float32, f.getframerate()


def _decode_wav_path(wav_path: Path) -> dict[str, str | float]:
    recognizer = _get_recognizer()
    samples, sample_rate = _read_wave(str(wav_path))
    stream = recognizer.create_stream()
    stream.accept_waveform(sample_rate, samples)
    recognizer.decode_stream(stream)
    transcript = str(stream.result.text).strip()
    default_conf = float(os.getenv("SHERPA_ONNX_DEFAULT_CONFIDENCE", "0.9"))
    confidence = default_conf if transcript else 0.0
    return {"transcript": transcript, "confidence": confidence}


def transcribe_file(audio_path: str | Path, mime_type: str = "audio/wav") -> dict[str, str | float]:
    """转码（如需）并识别音频文件。"""
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"audio file not found: {audio_path}")

    converted: Path | None = None
    try:
        wav_path = ensure_mono_wav(path, mime_type)
        if wav_path != path:
            converted = wav_path
        return _decode_wav_path(wav_path)
    except AudioConvertError as exc:
        raise AsrPipelineError(str(exc)) from exc
    except AsrPipelineError:
        raise
    except Exception as exc:
        logger.exception("ASR decode failed path=%s mime=%s", path, mime_type)
        raise AsrPipelineError(str(exc)) from exc
    finally:
        if converted is not None:
            converted.unlink(missing_ok=True)


def transcribe_audio(audio_payload: VoiceTurnPayload, mime_type: str = "audio/wav") -> dict[str, str | float]:
    """
    输入:
    - audio_payload.audio_path: 音频文件路径
    - mime_type: 原始 MIME（webm/wav 等）

    输出:
    - {"transcript": str, "confidence": float}
    """
    audio_path = str(audio_payload.audio_path).strip()
    if not audio_path:
        return {"transcript": "", "confidence": 0.0}
    return transcribe_file(audio_path, mime_type=mime_type)


def transcribe_bytes(audio_bytes: bytes, mime_type: str = "audio/webm") -> dict[str, str | float]:
    if not audio_bytes:
        return {"transcript": "", "confidence": 0.0}
    suffix = ".wav" if "wav" in mime_type else ".webm"
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="salary_battle_asr_") as tmp:
            tmp_path = tmp.name
            tmp.write(audio_bytes)
        return transcribe_file(tmp_path, mime_type=mime_type)
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
