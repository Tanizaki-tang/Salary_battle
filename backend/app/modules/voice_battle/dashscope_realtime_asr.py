from __future__ import annotations

import asyncio
import base64
import os
import threading
from dataclasses import dataclass
from typing import Any

from app.service.runtime_auth import get_runtime_auth


@dataclass(slots=True)
class AsrResult:
    partial: str
    is_final: bool
    final_text: str


def _env(name: str, default: str) -> str:
    value = (os.getenv(name) or "").strip()
    return value or default


def _clamp_float(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _load_api_key() -> str:
    runtime_auth = get_runtime_auth()
    if runtime_auth and runtime_auth.source == "user" and runtime_auth.user_api_key.strip():
        return runtime_auth.user_api_key.strip()
    api_key = (os.getenv("DASHSCOPE_API_KEY") or "").strip()
    if api_key:
        return api_key
    api_key = (os.getenv("BAILIAN_API_KEY") or "").strip()
    if api_key:
        return api_key
    raise ValueError("DASHSCOPE_API_KEY (or BAILIAN_API_KEY) is required for cloud realtime ASR.")


class DashScopeRealtimeAsr:
    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop,
        vad_threshold: float | None = None,
        silence_ms: int | None = None,
    ) -> None:
        import dashscope  # pyright: ignore[reportMissingImports]
        from dashscope.audio.qwen_omni import OmniRealtimeCallback, OmniRealtimeConversation  # pyright: ignore[reportMissingImports]
        from dashscope.audio.qwen_omni.omni_realtime import MultiModality, TranscriptionParams  # pyright: ignore[reportMissingImports]

        dashscope.api_key = _load_api_key()
        self._loop = loop
        self._sample_rate = int(_env("QWEN_ASR_SAMPLE_RATE", "16000"))
        self._vad_threshold = (
            _clamp_float(vad_threshold, 0.0, 1.0)
            if vad_threshold is not None
            else float(_env("QWEN_ASR_VAD_THRESHOLD", "0.0"))
        )
        self._silence_ms = (
            max(50, min(3000, int(silence_ms)))
            if silence_ms is not None
            else int(_env("QWEN_ASR_SILENCE_MS", "400"))
        )
        self._partial = ""
        self._results: asyncio.Queue[AsrResult] = asyncio.Queue()
        self._ready = threading.Event()
        self._closed = threading.Event()
        self._error: str | None = None
        self._multi_modality = MultiModality
        self._transcription_params = TranscriptionParams(
            language=_env("QWEN_ASR_LANGUAGE", "zh"),
            sample_rate=self._sample_rate,
            input_audio_format="pcm",
        )

        outer = self

        class _Cb(OmniRealtimeCallback):
            def on_open(self) -> None:
                outer._ready.set()

            def on_close(self, code: int, msg: str) -> None:
                outer._closed.set()

            def on_event(self, response: dict[str, Any]) -> None:
                outer._handle_event(response)

            def on_error(self, error: Any) -> None:
                outer._error = str(error)
                outer._closed.set()

        self._callback = _Cb()
        self._conversation = OmniRealtimeConversation(
            model=_env("QWEN_ASR_MODEL", "qwen3-asr-flash-realtime"),
            callback=self._callback,
            api_key=_load_api_key(),
            url=_env("QWEN_ASR_WS_URL", "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"),
        )

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def connect(self) -> None:
        self._conversation.connect()
        if not self._ready.wait(timeout=10):
            raise RuntimeError("cloud ASR connect timeout")
        self._conversation.update_session(
            output_modalities=[self._multi_modality.TEXT],
            enable_input_audio_transcription=True,
            input_audio_transcription_model=_env("QWEN_ASR_TRANSCRIPTION_MODEL", ""),
            enable_turn_detection=True,
            turn_detection_type="server_vad",
            turn_detection_threshold=self._vad_threshold,
            turn_detection_silence_duration_ms=self._silence_ms,
            transcription_params=self._transcription_params,
        )

    def append_audio(self, pcm16le: bytes) -> None:
        if not pcm16le:
            return
        self._conversation.append_audio(base64.b64encode(pcm16le).decode("ascii"))

    def drain_results(self) -> list[AsrResult]:
        rows: list[AsrResult] = []
        while True:
            try:
                rows.append(self._results.get_nowait())
            except asyncio.QueueEmpty:
                break
        if self._error:
            raise RuntimeError(self._error)
        return rows

    def close(self) -> None:
        try:
            self._conversation.end_session()
        except Exception:
            try:
                self._conversation.close()
            except Exception:
                pass

    def debug_info(self) -> dict[str, Any]:
        return {
            "sample_rate": self._sample_rate,
            "provider": "dashscope",
            "vad_threshold": self._vad_threshold,
            "silence_ms": self._silence_ms,
        }

    def _handle_event(self, response: dict[str, Any]) -> None:
        event_type = str(response.get("type") or "")
        if event_type == "conversation.item.input_audio_transcription.text":
            partial = str(response.get("stash") or response.get("text") or "").strip()
            self._partial = partial
            self._loop.call_soon_threadsafe(
                self._results.put_nowait,
                AsrResult(partial=partial, is_final=False, final_text=""),
            )
            return
        if event_type == "conversation.item.input_audio_transcription.completed":
            final_text = str(response.get("transcript") or response.get("text") or "").strip()
            self._partial = ""
            self._loop.call_soon_threadsafe(
                self._results.put_nowait,
                AsrResult(partial=final_text, is_final=True, final_text=final_text),
            )
