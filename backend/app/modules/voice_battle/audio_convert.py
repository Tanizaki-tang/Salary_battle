from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path


class AudioConvertError(RuntimeError):
    """音频转码失败（FFmpeg 缺失、格式不支持等）。"""


def resolve_ffmpeg_path() -> str | None:
    configured = os.getenv("FFMPEG_PATH", "").strip()
    if configured and Path(configured).exists():
        return configured
    return shutil.which("ffmpeg")


def ffmpeg_available() -> bool:
    return resolve_ffmpeg_path() is not None


def is_valid_mono_wav(path: Path, *, sample_rate: int = 16000) -> bool:
    try:
        with wave.open(str(path)) as wf:
            return wf.getnchannels() == 1 and wf.getsampwidth() == 2 and wf.getframerate() == sample_rate
    except wave.Error:
        return False


def ensure_mono_wav(input_path: str | Path, mime_type: str = "audio/wav", *, sample_rate: int = 16000) -> Path:
    """将输入音频规范为 mono 16-bit PCM WAV（16kHz）。已是合法 WAV 则直通。"""
    src = Path(input_path)
    if not src.exists():
        raise FileNotFoundError(f"audio file not found: {input_path}")

    mime = (mime_type or "").split(";")[0].strip().lower()
    suffix = src.suffix.lower()
    is_wav = mime in {"audio/wav", "audio/x-wav", "audio/wave"} or suffix == ".wav"
    if is_wav and is_valid_mono_wav(src, sample_rate=sample_rate):
        return src

    ffmpeg = resolve_ffmpeg_path()
    if not ffmpeg:
        raise AudioConvertError(
            "FFmpeg not found. Install FFmpeg and add it to PATH, or set FFMPEG_PATH in .env."
        )

    out_fd, out_name = tempfile.mkstemp(suffix=".wav", prefix="salary_battle_wav_")
    os.close(out_fd)
    out_path = Path(out_name)
    try:
        cmd = [
            ffmpeg,
            "-y",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-sample_fmt",
            "s16",
            str(out_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[-500:]
            raise AudioConvertError(f"FFmpeg conversion failed: {detail}")
        if not out_path.exists() or out_path.stat().st_size == 0:
            raise AudioConvertError("FFmpeg produced an empty wav file.")
        return out_path
    except Exception:
        out_path.unlink(missing_ok=True)
        raise
