from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

try:
    import websockets
except ImportError:  # pragma: no cover
    websockets = None  # type: ignore[assignment]


AsrPartialCallback = Callable[[str], Awaitable[None]]
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BailianAsrConfig:
    url: str
    api_key: str
    model: str
    audio_format: str
    sample_rate: int
    semantic_punctuation_enabled: bool = False
    max_sentence_silence: int = 800
    punctuation_prediction_enabled: bool = True
    inverse_text_normalization_enabled: bool = True


class BailianAsrError(RuntimeError):
    pass


def _load_config_from_env() -> BailianAsrConfig:
    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise BailianAsrError("Missing DASHSCOPE_API_KEY for Bailian realtime ASR.")
    url = os.getenv("BAILIAN_ASR_WS_URL", "wss://dashscope.aliyuncs.com/api-ws/v1/inference").strip()
    model = os.getenv("BAILIAN_ASR_MODEL", "paraformer-realtime-v2").strip() or "paraformer-realtime-v2"
    audio_format = os.getenv("BAILIAN_ASR_FORMAT", "pcm").strip() or "pcm"
    sample_rate = int(os.getenv("BAILIAN_ASR_SAMPLE_RATE", "16000"))
    semantic_punctuation_enabled = os.getenv("BAILIAN_ASR_SEMANTIC_PUNCT", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    max_sentence_silence = int(os.getenv("BAILIAN_ASR_MAX_SILENCE_MS", "800"))
    punctuation_prediction_enabled = os.getenv("BAILIAN_ASR_PUNCT", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    inverse_text_normalization_enabled = os.getenv("BAILIAN_ASR_ITN", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }
    return BailianAsrConfig(
        url=url,
        api_key=api_key,
        model=model,
        audio_format=audio_format,
        sample_rate=sample_rate,
        semantic_punctuation_enabled=semantic_punctuation_enabled,
        max_sentence_silence=max_sentence_silence,
        punctuation_prediction_enabled=punctuation_prediction_enabled,
        inverse_text_normalization_enabled=inverse_text_normalization_enabled,
    )


class BailianRealtimeAsrSession:
    def __init__(self, *, on_partial: AsrPartialCallback) -> None:
        self._cfg = _load_config_from_env()
        self._on_partial = on_partial
        self._task_id = str(uuid.uuid4())
        self._ws: Any | None = None
        self._recv_task: asyncio.Task[None] | None = None
        self._started = asyncio.Event()
        self._final_future: asyncio.Future[str] | None = None
        self._last_partial: str = ""
        self._connect_started_at: float | None = None
        self._task_started_at: float | None = None
        self._first_partial_at: float | None = None
        self._finish_called_at: float | None = None

    async def start(self) -> None:
        if websockets is None:
            raise BailianAsrError("Missing dependency `websockets`. Please install it.")
        if self._ws is not None:
            return
        self._connect_started_at = time.perf_counter()
        headers = {"Authorization": f"Bearer {self._cfg.api_key}", "user-agent": "salary-battle"}
        self._ws = await websockets.connect(self._cfg.url, extra_headers=headers)  # type: ignore[attr-defined]
        self._final_future = asyncio.get_running_loop().create_future()
        self._recv_task = asyncio.create_task(self._recv_loop())
        await self._send_run_task()
        try:
            await asyncio.wait_for(self._started.wait(), timeout=10)
        except TimeoutError as exc:
            raise BailianAsrError("Bailian ASR task-started timeout.") from exc

    async def send_audio(self, pcm_bytes: bytes) -> None:
        if not pcm_bytes:
            return
        await self.start()
        assert self._ws is not None
        await self._ws.send(pcm_bytes)

    async def finish_and_get_final(self, *, timeout: float = 10.0) -> str:
        if self._ws is None:
            return ""
        self._finish_called_at = time.perf_counter()
        await self._send_finish_task()
        fut = self._final_future
        if fut is None:
            return ""
        try:
            text = await asyncio.wait_for(fut, timeout=timeout)
            return text.strip()
        except TimeoutError:
            return self._last_partial.strip()

    async def close(self) -> None:
        if self._recv_task:
            self._recv_task.cancel()
            try:
                await self._recv_task
            except Exception:
                pass
            self._recv_task = None
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def _send_run_task(self) -> None:
        assert self._ws is not None
        payload: dict[str, Any] = {
            "task_group": "audio",
            "task": "asr",
            "function": "recognition",
            "model": self._cfg.model,
            "parameters": {
                "format": self._cfg.audio_format,
                "sample_rate": self._cfg.sample_rate,
                "semantic_punctuation_enabled": self._cfg.semantic_punctuation_enabled,
                "max_sentence_silence": self._cfg.max_sentence_silence,
                "punctuation_prediction_enabled": self._cfg.punctuation_prediction_enabled,
                "inverse_text_normalization_enabled": self._cfg.inverse_text_normalization_enabled,
            },
            "input": {},
        }
        msg = {
            "header": {"action": "run-task", "task_id": self._task_id, "streaming": "duplex"},
            "payload": payload,
        }
        await self._ws.send(json.dumps(msg, ensure_ascii=False))

    async def _send_finish_task(self) -> None:
        assert self._ws is not None
        msg = {
            "header": {"action": "finish-task", "task_id": self._task_id, "streaming": "duplex"},
            "payload": {"input": {}},
        }
        await self._ws.send(json.dumps(msg, ensure_ascii=False))

    async def _recv_loop(self) -> None:
        assert self._ws is not None
        while True:
            raw = await self._ws.recv()
            if not isinstance(raw, (str, bytes)):
                continue
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="ignore")
            data = json.loads(raw)
            header = data.get("header", {}) if isinstance(data.get("header"), dict) else {}
            event = str(header.get("event", "")).strip()
            if event == "task-started":
                self._started.set()
                self._task_started_at = time.perf_counter()
                if _latency_enabled() and self._connect_started_at is not None:
                    logger.info(
                        "bailian_asr task_started model=%s sr=%s connect_ms=%.1f",
                        self._cfg.model,
                        self._cfg.sample_rate,
                        (self._task_started_at - self._connect_started_at) * 1000,
                    )
                continue
            if event != "result-generated":
                continue
            payload = data.get("payload", {}) if isinstance(data.get("payload"), dict) else {}
            output = payload.get("output", {}) if isinstance(payload.get("output"), dict) else {}
            sentence = output.get("sentence", {}) if isinstance(output.get("sentence"), dict) else {}
            text = str(sentence.get("text", "")).strip()
            if not text:
                continue
            self._last_partial = text
            now = time.perf_counter()
            if self._first_partial_at is None:
                self._first_partial_at = now
                if _latency_enabled() and self._task_started_at is not None:
                    logger.info(
                        "bailian_asr first_partial model=%s text_len=%s after_task_ms=%.1f",
                        self._cfg.model,
                        len(text),
                        (now - self._task_started_at) * 1000,
                    )
            await self._on_partial(text)
            sentence_end = bool(sentence.get("sentence_end", False))
            end_time = sentence.get("end_time", None)
            if sentence_end or end_time is not None:
                fut = self._final_future
                if fut is not None and not fut.done():
                    fut.set_result(text)
                    if _latency_enabled():
                        after_finish_ms = None
                        if self._finish_called_at is not None:
                            after_finish_ms = (time.perf_counter() - self._finish_called_at) * 1000
                        logger.info(
                            "bailian_asr final text_len=%s sentence_end=%s after_finish_ms=%s",
                            len(text),
                            sentence_end,
                            f"{after_finish_ms:.1f}" if after_finish_ms is not None else "",
                        )


def _latency_enabled() -> bool:
    value = os.getenv("REALTIME_LATENCY_LOG", "").strip().lower()
    return value in {"1", "true", "yes", "on"}
