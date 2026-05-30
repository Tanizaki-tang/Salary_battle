from __future__ import annotations

import os
import subprocess
import tempfile
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.shared_types.game_types import VoiceTurnPayload


TARGET_SAMPLE_RATE = 16000


class SpeechRecognitionError(RuntimeError):
    pass


def transcribe_audio(audio_payload: VoiceTurnPayload) -> dict:
    audio_path = Path(audio_payload.audio_path)
    if not audio_path.is_file():
        raise SpeechRecognitionError(f"Audio file not found: {audio_path}")

    wav_path: Path | None = None
    try:
        source_path = audio_path
        if audio_path.suffix.lower() != ".wav":
            wav_path = _convert_to_wav(audio_path)
            source_path = wav_path

        try:
            samples, sample_rate = _read_wav(source_path)
            if sample_rate != TARGET_SAMPLE_RATE:
                wav_path = _convert_to_wav(audio_path)
                samples, sample_rate = _read_wav(wav_path)
        except SpeechRecognitionError:
            wav_path = _convert_to_wav(audio_path)
            samples, sample_rate = _read_wav(wav_path)

        recognizer = _get_recognizer()
        stream = recognizer.create_stream()
        stream.accept_waveform(sample_rate, samples)
        recognizer.decode_stream(stream)

        transcript = getattr(stream.result, "text", "").strip()
        if not transcript:
            raise SpeechRecognitionError("ASR returned empty transcript")

        return {"transcript": transcript, "confidence": 0.95}
    except FileNotFoundError as exc:
        raise SpeechRecognitionError("ffmpeg is required for this audio format") from exc
    except subprocess.CalledProcessError as exc:
        raise SpeechRecognitionError(f"ffmpeg failed to convert audio: {exc}") from exc
    finally:
        if wav_path and wav_path != audio_path:
            wav_path.unlink(missing_ok=True)


@lru_cache(maxsize=1)
def _get_recognizer():
    try:
        import sherpa_onnx
    except ImportError as exc:
        raise SpeechRecognitionError("sherpa-onnx is not installed in this Python environment") from exc

    model_dir = _model_dir()
    model_type = os.getenv("SHERPA_ONNX_MODEL_TYPE", "sense_voice").lower()
    provider = os.getenv("SHERPA_ONNX_PROVIDER", "cpu")
    num_threads = int(os.getenv("SHERPA_ONNX_NUM_THREADS", "2"))

    if model_type == "sense_voice":
        return sherpa_onnx.OfflineRecognizer.from_sense_voice(
            model=str(_first_existing(model_dir, ["model.int8.onnx", "model.onnx"])),
            tokens=str(_required_file(model_dir / "tokens.txt")),
            num_threads=num_threads,
            sample_rate=TARGET_SAMPLE_RATE,
            feature_dim=80,
            decoding_method="greedy_search",
            provider=provider,
            use_itn=True,
            debug=False,
        )

    if model_type == "paraformer":
        return sherpa_onnx.OfflineRecognizer.from_paraformer(
            paraformer=str(_first_existing(model_dir, ["model.int8.onnx", "model.onnx"])),
            tokens=str(_required_file(model_dir / "tokens.txt")),
            num_threads=num_threads,
            sample_rate=TARGET_SAMPLE_RATE,
            feature_dim=80,
            decoding_method="greedy_search",
            provider=provider,
            debug=False,
        )

    if model_type == "transducer":
        return sherpa_onnx.OfflineRecognizer.from_transducer(
            encoder=str(_first_existing(model_dir, ["encoder.int8.onnx", "encoder.onnx"])),
            decoder=str(_first_existing(model_dir, ["decoder.int8.onnx", "decoder.onnx"])),
            joiner=str(_first_existing(model_dir, ["joiner.int8.onnx", "joiner.onnx"])),
            tokens=str(_required_file(model_dir / "tokens.txt")),
            num_threads=num_threads,
            sample_rate=TARGET_SAMPLE_RATE,
            feature_dim=80,
            decoding_method="greedy_search",
            provider=provider,
            debug=False,
        )

    if model_type == "whisper":
        return sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=str(_required_file(model_dir / "encoder.onnx")),
            decoder=str(_required_file(model_dir / "decoder.onnx")),
            tokens=str(_required_file(model_dir / "tokens.txt")),
            num_threads=num_threads,
            decoding_method="greedy_search",
            provider=provider,
            debug=False,
        )

    raise SpeechRecognitionError(f"Unsupported SHERPA_ONNX_MODEL_TYPE: {model_type}")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _model_dir() -> Path:
    configured = os.getenv("SHERPA_ONNX_MODEL_DIR")
    path = Path(configured) if configured else _repo_root() / "resources" / "sherpa-onnx-models"
    if not path.is_dir():
        raise SpeechRecognitionError(f"Sherpa-ONNX model directory not found: {path}")
    return path


def _required_file(path: Path) -> Path:
    if not path.is_file():
        raise SpeechRecognitionError(f"Sherpa-ONNX model file not found: {path}")
    return path


def _first_existing(directory: Path, names: list[str]) -> Path:
    for name in names:
        path = directory / name
        if path.is_file():
            return path
    expected = ", ".join(names)
    raise SpeechRecognitionError(f"Missing model file in {directory}. Expected one of: {expected}")


def _convert_to_wav(audio_path: Path) -> Path:
    with tempfile.NamedTemporaryFile(prefix="salary_battle_asr_", suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-nostdin",
            "-loglevel",
            "error",
            "-i",
            str(audio_path),
            "-ac",
            "1",
            "-ar",
            str(TARGET_SAMPLE_RATE),
            "-f",
            "wav",
            str(wav_path),
        ],
        check=True,
    )
    return wav_path


def _read_wav(wav_path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(wav_path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frames = wav_file.readframes(wav_file.getnframes())

    if channels != 1 or sample_width != 2:
        raise SpeechRecognitionError("Audio must be mono 16-bit PCM wav before recognition")

    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, sample_rate
