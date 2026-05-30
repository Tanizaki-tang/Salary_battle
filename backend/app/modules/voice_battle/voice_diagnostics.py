from __future__ import annotations

import os
from typing import Any

from app.modules.voice_battle.tts_gateway import get_tts_config_summary, probe_tts_load, probe_tts_sample

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

def _realtime_asr_configured() -> bool:
    return bool(os.getenv("DASHSCOPE_API_KEY", "").strip())


def run_voice_diagnostics() -> dict[str, Any]:
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

    recommendations: list[str] = []

    if not _realtime_asr_configured():
        recommendations.append("Set DASHSCOPE_API_KEY for Bailian realtime ASR.")
    if backend_tts_required and not tts_summary.get("files_ok"):
        recommendations.append(
            "Download sherpa-onnx-vits-zh-ll and set SHERPA_ONNX_TTS_MODEL_DIR. See README TTS section."
        )
    if backend_tts_required and tts_summary.get("files_ok") and not tts_load_ok:
        recommendations.append(f"TTS model failed to load: {tts_load_error}")
    if not _llm_configured():
        recommendations.append("Set BAILIAN_API_KEY for HR Agent LLM replies.")

    ready = _realtime_asr_configured() and _llm_configured()
    if backend_tts_required:
        ready = ready and tts_summary.get("files_ok", False) and tts_load_ok

    return {
        "ready": ready,
        "checks": {
            "realtime_asr_configured": _realtime_asr_configured(),
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
