from __future__ import annotations

import asyncio
import json
import os
import threading
from dataclasses import dataclass
from typing import Any, Callable


def _load_api_key() -> str:
    api_key = (os.getenv("DASHSCOPE_API_KEY") or "").strip()
    if api_key:
        return api_key
    api_key = (os.getenv("BAILIAN_API_KEY") or "").strip()
    if api_key:
        return api_key
    raise ValueError("DASHSCOPE_API_KEY (or BAILIAN_API_KEY) is required for QwenTTS.")


def _env(name: str, default: str) -> str:
    value = (os.getenv(name) or "").strip()
    return value or default


@dataclass(slots=True)
class QwenTtsConfig:
    model: str
    voice: str
    url: str


def load_qwen_tts_config() -> QwenTtsConfig:
    return QwenTtsConfig(
        model=_env("QWEN_TTS_MODEL", "qwen3-tts-flash-realtime"),
        voice=_env("QWEN_TTS_VOICE", "Cherry"),
        url=_env("QWEN_TTS_WS_URL", "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"),
    )


class QwenTtsRealtimeSession:
    def __init__(self, *, loop: asyncio.AbstractEventLoop, on_event: Callable[[dict[str, Any]], None]) -> None:
        import dashscope  # pyright: ignore[reportMissingImports]
        from dashscope.audio.qwen_tts_realtime import (  # pyright: ignore[reportMissingImports]
            AudioFormat,
            QwenTtsRealtime,
            QwenTtsRealtimeCallback,
        )

        dashscope.api_key = _load_api_key()
        cfg = load_qwen_tts_config()

        self._loop = loop
        self._on_event = on_event
        self._done = threading.Event()
        self._last_error: str | None = None

        outer = self

        class _Cb(QwenTtsRealtimeCallback):
            def on_event(self, response: Any) -> None:
                try:
                    payload: dict[str, Any]
                    if isinstance(response, str):
                        payload = json.loads(response)
                    else:
                        payload = response
                    outer._loop.call_soon_threadsafe(outer._on_event, payload)
                    if payload.get("type") in {"session.finished"}:
                        outer._done.set()
                except Exception as exc:
                    outer._last_error = str(exc)
                    outer._done.set()

            def on_close(self, close_status_code: int, close_msg: str) -> None:
                outer._done.set()

        self._callback = _Cb()
        self._tts = QwenTtsRealtime(model=cfg.model, callback=self._callback, url=cfg.url)
        self._audio_format = AudioFormat.PCM_24000HZ_MONO_16BIT
        self._voice = cfg.voice

    def connect(self) -> None:
        self._tts.connect()
        self._tts.update_session(
            voice=self._voice,
            response_format=self._audio_format,
            mode="server_commit",
            language_type=_env("QWEN_TTS_LANGUAGE_TYPE", "Chinese"),
        )

    def append_text(self, text: str) -> None:
        if text:
            self._tts.append_text(text)

    def finish(self) -> None:
        self._tts.finish()

    def wait_closed(self, timeout_s: float = 20.0) -> None:
        self._done.wait(timeout=timeout_s)
        if self._last_error:
            raise RuntimeError(self._last_error)

