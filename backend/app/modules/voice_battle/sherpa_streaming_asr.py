from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class AsrResult:
    partial: str
    is_final: bool
    final_text: str


def _env_float(name: str, default: float) -> float:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _resolve_model_dir() -> Path:
    raw = (os.getenv("SHERPA_ONNX_STREAMING_ASR_DIR") or "").strip()
    if raw:
        p = Path(raw)
        if p.exists():
            return p
    return Path(__file__).resolve().parents[4] / "models" / "sherpa-onnx-asr"


def _looks_like_streaming_dir(p: Path) -> bool:
    if not p.is_dir():
        return False
    if not (p / "tokens.txt").exists():
        return False
    if (p / "joiner.onnx").exists() or (p / "joiner.int8.onnx").exists():
        return True
    if (p / "encoder.onnx").exists() or (p / "encoder.int8.onnx").exists():
        if (p / "decoder.onnx").exists() or (p / "decoder.int8.onnx").exists():
            return True
    if (p / "encoder.int8.onnx").exists() and (p / "decoder.int8.onnx").exists():
        return True
    if (p / "paraformer-encoder.onnx").exists() or (p / "paraformer-encoder.int8.onnx").exists():
        if (p / "paraformer-decoder.onnx").exists() or (p / "paraformer-decoder.int8.onnx").exists():
            return True
    return False


def _auto_pick_streaming_model_dir(root: Path) -> Path | None:
    candidates: list[Path] = []
    for p in [root, root / "sherpa-onnx-asr"]:
        if p.is_dir():
            candidates.append(p)

    for base in candidates:
        if _looks_like_streaming_dir(base):
            return base
        for child in base.iterdir():
            if child.is_dir() and _looks_like_streaming_dir(child):
                return child
    return None


def _pick_file(model_dir: Path, *candidates: str) -> Path:
    for c in candidates:
        p = model_dir / c
        if p.exists():
            return p
    raise FileNotFoundError(f"missing model file in {model_dir}")


class SherpaStreamingAsr:
    def __init__(
        self,
        *,
        rule1_min_trailing_silence: float | None = None,
        rule2_min_trailing_silence: float | None = None,
        rule3_min_utterance_length: float | None = None,
    ) -> None:
        import sherpa_onnx  # pyright: ignore[reportMissingImports]

        raw_dir = _resolve_model_dir()
        model_dir = _auto_pick_streaming_model_dir(raw_dir) or raw_dir
        tokens = _pick_file(model_dir, "tokens.txt")

        encoder = None
        decoder = None
        joiner = None
        paraformer_encoder = None
        paraformer_decoder = None

        for name in ("encoder.onnx", "encoder.int8.onnx"):
            p = model_dir / name
            if p.exists():
                encoder = p
                break
        for name in ("decoder.onnx", "decoder.int8.onnx"):
            p = model_dir / name
            if p.exists():
                decoder = p
                break
        for name in ("joiner.onnx", "joiner.int8.onnx"):
            p = model_dir / name
            if p.exists():
                joiner = p
                break

        for name in ("paraformer-encoder.onnx", "paraformer-encoder.int8.onnx"):
            p = model_dir / name
            if p.exists():
                paraformer_encoder = p
                break
        for name in ("paraformer-decoder.onnx", "paraformer-decoder.int8.onnx"):
            p = model_dir / name
            if p.exists():
                paraformer_decoder = p
                break

        if paraformer_encoder is None:
            for name in ("encoder.onnx", "encoder.int8.onnx"):
                p = model_dir / name
                if p.exists():
                    paraformer_encoder = p
                    break
        if paraformer_decoder is None:
            for name in ("decoder.onnx", "decoder.int8.onnx"):
                p = model_dir / name
                if p.exists():
                    paraformer_decoder = p
                    break

        sample_rate = _env_int("SHERPA_ONNX_ASR_SAMPLE_RATE", 16000)
        feature_dim = _env_int("SHERPA_ONNX_ASR_FEATURE_DIM", 80)
        num_threads = _env_int("SHERPA_ONNX_ASR_NUM_THREADS", 2)

        enable_endpoint_detection = True
        rule1 = (
            float(rule1_min_trailing_silence)
            if rule1_min_trailing_silence is not None
            else _env_float("SHERPA_ONNX_ASR_RULE1_MIN_TRAILING_SILENCE", 2.0)
        )
        rule2 = (
            float(rule2_min_trailing_silence)
            if rule2_min_trailing_silence is not None
            else _env_float("SHERPA_ONNX_ASR_RULE2_MIN_TRAILING_SILENCE", 1.0)
        )
        rule3 = (
            float(rule3_min_utterance_length)
            if rule3_min_utterance_length is not None
            else _env_float("SHERPA_ONNX_ASR_RULE3_MIN_UTTERANCE_LENGTH", 20.0)
        )

        if encoder and decoder and joiner:
            self._recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
                tokens=str(tokens),
                encoder=str(encoder),
                decoder=str(decoder),
                joiner=str(joiner),
                num_threads=num_threads,
                sample_rate=sample_rate,
                feature_dim=feature_dim,
                enable_endpoint_detection=enable_endpoint_detection,
                rule1_min_trailing_silence=rule1,
                rule2_min_trailing_silence=rule2,
                rule3_min_utterance_length=rule3,
            )
        elif paraformer_encoder and paraformer_decoder:
            self._recognizer = sherpa_onnx.OnlineRecognizer.from_paraformer(
                tokens=str(tokens),
                encoder=str(paraformer_encoder),
                decoder=str(paraformer_decoder),
                num_threads=num_threads,
                sample_rate=sample_rate,
                feature_dim=feature_dim,
                enable_endpoint_detection=enable_endpoint_detection,
                rule1_min_trailing_silence=rule1,
                rule2_min_trailing_silence=rule2,
                rule3_min_utterance_length=rule3,
            )
        else:
            raise FileNotFoundError(
                "No streaming ASR model found. Set SHERPA_ONNX_STREAMING_ASR_DIR to a directory containing "
                "tokens.txt and either (encoder+decoder+joiner) or (paraformer-encoder+paraformer-decoder). "
                "If you only have *.tar.bz2, extract one streaming model first."
            )

        self._stream = self._recognizer.create_stream()
        self._last_partial = ""
        self._sample_rate = sample_rate

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def accept_pcm16le(self, pcm16le: bytes, *, sample_rate: int) -> AsrResult:
        import numpy as np  # pyright: ignore[reportMissingImports]

        if not pcm16le:
            return AsrResult(partial=self._last_partial, is_final=False, final_text="")

        samples_int16 = np.frombuffer(pcm16le, dtype=np.int16)
        samples = samples_int16.astype(np.float32) / 32768.0

        self._stream.accept_waveform(sample_rate, samples)
        while self._recognizer.is_ready(self._stream):
            self._recognizer.decode_stream(self._stream)

        result = self._recognizer.get_result(self._stream)
        is_endpoint = self._recognizer.is_endpoint(self._stream)

        partial = (result or "").strip()
        self._last_partial = partial

        if is_endpoint:
            final_text = partial
            if final_text:
                self._recognizer.reset(self._stream)
            self._last_partial = ""
            return AsrResult(partial=partial, is_final=True, final_text=final_text)

        return AsrResult(partial=partial, is_final=False, final_text="")

    def debug_info(self) -> dict[str, Any]:
        return {"sample_rate": self._sample_rate}
