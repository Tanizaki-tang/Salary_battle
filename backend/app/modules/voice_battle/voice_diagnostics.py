from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.modules.voice_battle.audio_convert import ffmpeg_available, resolve_ffmpeg_path
from app.modules.voice_battle.speech_gateway import (
    get_asr_config_summary,
    probe_asr_load,
    probe_sample_transcript,
    sherpa_onnx_installed,
)
from app.modules.voice_battle.tts_gateway import get_tts_config_summary, probe_tts_load, probe_tts_sample

try:
    from dotenv import load_dotenv

    PROJECT_ROOT = Path(__file__).resolve().parents[4]
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass


def _llm_configured() -> bool:
    return bool(os.getenv("BAILIAN_API_KEY", "").strip())


def _realtime_ws_enabled() -> bool:
    value = os.getenv("REALTIME_WS_ENABLED", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _tts_enabled() -> bool:
    value = os.getenv("REALTIME_TTS_ENABLED", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _tts_mode() -> bool:
    value = os.getenv("REALTIME_TTS_MODE", "browser").strip().lower()
    return value in {"backend", "server"}


def run_voice_diagnostics() -> dict[str, Any]:
    asr_summary = get_asr_config_summary()
    load_ok = False
    load_error = ""
    sample_transcript = ""
    sample_error = ""

    if asr_summary.get("files_ok"):
        load_ok, load_error = probe_asr_load()
        if load_ok:
            sample_transcript, sample_error = probe_sample_transcript()

    tts_summary = get_tts_config_summary()
    tts_load_ok = False
    tts_load_error = ""
    tts_sample = ""
    tts_sample_error = ""
    backend_tts_required = _tts_enabled() and _tts_mode()

    if backend_tts_required:
        if tts_summary.get("files_ok"):
            tts_load_ok, tts_load_error = probe_tts_load()
            if tts_load_ok:
                tts_sample, tts_sample_error = probe_tts_sample()
        else:
            tts_load_error = "TTS model files missing"

    ffmpeg_ok = ffmpeg_available()
    recommendations: list[str] = []

    if not sherpa_onnx_installed():
        recommendations.append("Install Python package: pip install sherpa-onnx numpy")
    if not asr_summary.get("files_ok"):
        recommendations.append(
            "Download offline paraformer model and set SHERPA_ONNX_MODEL_DIR. "
            "See README voice ASR section."
        )
    if asr_summary.get("files_ok") and not load_ok:
        recommendations.append(f"ASR model failed to load: {load_error}")
    if backend_tts_required and not tts_summary.get("files_ok"):
        recommendations.append(
            "Download sherpa-onnx-vits-zh-ll and set SHERPA_ONNX_TTS_MODEL_DIR. See README TTS section."
        )
    if backend_tts_required and tts_summary.get("files_ok") and not tts_load_ok:
        recommendations.append(f"TTS model failed to load: {tts_load_error}")
    if not ffmpeg_ok:
        recommendations.append("Install FFmpeg and add to PATH, or set FFMPEG_PATH in .env.")
    if not _llm_configured():
        recommendations.append("Set BAILIAN_API_KEY for HR Agent LLM replies.")

    ready = (
        sherpa_onnx_installed()
        and ffmpeg_ok
        and asr_summary.get("files_ok", False)
        and load_ok
        and _llm_configured()
    )
    if backend_tts_required:
        ready = ready and tts_summary.get("files_ok", False) and tts_load_ok

    return {
        "ready": ready,
        "checks": {
            "sherpa_onnx_installed": sherpa_onnx_installed(),
            "ffmpeg_available": ffmpeg_ok,
            "ffmpeg_path": resolve_ffmpeg_path(),
            "asr_model": {
                **asr_summary,
                "load_ok": load_ok,
                "load_error": load_error or None,
                "sample_transcript": sample_transcript or None,
                "sample_error": sample_error or None,
            },
            "tts_model": {
                **tts_summary,
                "enabled": _tts_enabled(),
                "mode": "backend" if backend_tts_required else "browser",
                "load_ok": tts_load_ok if backend_tts_required else None,
                "load_error": tts_load_error or None,
                "sample": tts_sample or None,
                "sample_error": tts_sample_error or None,
            },
            "realtime_ws_enabled": _realtime_ws_enabled(),
            "llm_configured": _llm_configured(),
        },
        "recommendations": recommendations,
    }
