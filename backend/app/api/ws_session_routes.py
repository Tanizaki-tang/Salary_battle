from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.api.session_routes import SESSIONS, orchestrator
from app.modules.voice_battle.opening_service import resolve_hr_opening
from app.modules.voice_battle.realtime_voice_service import RealtimeVoiceService
from app.modules.voice_battle.speech_gateway import AsrPipelineError
from app.modules.voice_battle.bailian_realtime_asr import BailianAsrError, BailianRealtimeAsrSession
from app.modules.voice_battle.tts_gateway import synthesize_wav_base64
from app.modules.voice_battle.tts_voice_map import resolve_tts_speaker_id

WS_PATH = "/api/v1/ws/sessions/{session_id}"

router = APIRouter(tags=["realtime"])
logger = logging.getLogger(__name__)


@router.websocket(WS_PATH)
async def ws_session_stream(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    if not _ws_enabled():
        await _send_event(websocket, "server.error", {"message": "Realtime websocket disabled by config."})
        await websocket.close(code=1008)
        return

    session = SESSIONS.get(session_id)
    if session is None:
        await _send_event(websocket, "server.error", {"message": "session not found", "session_id": session_id})
        await websocket.close(code=1008)
        return

    voice_service = RealtimeVoiceService()
    asr_session: BailianRealtimeAsrSession | None = None
    seq = 0
    tts_buffer = ""
    hr_speaking_sent = False
    utterance_id = 0
    utterance_started_at: float | None = None
    utterance_first_chunk_at: float | None = None
    utterance_bytes = 0
    voice_chunk_count = 0
    asr_first_partial_at: float | None = None
    commit_called_at: float | None = None
    turn_started_at: float | None = None
    first_hr_delta_at: float | None = None
    first_tts_audio_at: float | None = None
    loop = asyncio.get_running_loop()
    emit_futures: list[asyncio.Future[Any]] = []

    async def emit_call_state(phase: str) -> bool:
        return await _send_event(websocket, "server.call_state", {"phase": phase, "session_id": session_id})

    async def emit_hr_delta(chunk: str) -> None:
        nonlocal seq
        nonlocal tts_buffer
        nonlocal hr_speaking_sent
        nonlocal first_tts_audio_at
        seq += 1
        await _send_event(websocket, "server.hr_delta", {"delta": chunk, "session_id": session_id}, seq=seq)
        if _tts_enabled():
            if _tts_mode() == "backend":
                tts_buffer += chunk
                if _should_flush_tts(tts_buffer, chunk):
                    sid = resolve_tts_speaker_id(session.hr_personality_id)
                    t0 = time.perf_counter()
                    audio_payload = synthesize_wav_base64(tts_buffer, speaker_id=sid)
                    if _latency_enabled():
                        t1 = time.perf_counter()
                        if first_tts_audio_at is None:
                            first_tts_audio_at = t1
                        logger.info(
                            "latency tts_synth session_id=%s utterance_id=%s synth_ms=%.1f text_len=%s",
                            session_id,
                            utterance_id,
                            (t1 - t0) * 1000,
                            len(tts_buffer),
                        )
                    if not hr_speaking_sent:
                        hr_speaking_sent = True
                        await emit_call_state("speaking")
                    await _send_event(
                        websocket,
                        "server.hr_audio_chunk",
                        {**audio_payload, "text": tts_buffer, "session_id": session_id},
                        seq=seq,
                    )
                    tts_buffer = ""
            else:
                if not hr_speaking_sent:
                    hr_speaking_sent = True
                    await emit_call_state("speaking")
                await _send_event(websocket, "server.hr_audio_chunk", {"text": chunk, "session_id": session_id}, seq=seq)

    async def emit_hr_opening() -> None:
        nonlocal hr_speaking_sent
        opening = resolve_hr_opening(session)
        if not opening:
            await emit_call_state("listening")
            return
        try:
            hr_speaking_sent = True
            await emit_call_state("speaking")
            payload: dict[str, Any] = {"text": opening, "session_id": session_id}
            if _tts_enabled() and _tts_mode() == "backend":
                sid = resolve_tts_speaker_id(session.hr_personality_id)
                audio_payload = await asyncio.to_thread(
                    lambda: synthesize_wav_base64(opening, speaker_id=sid)
                )
                payload.update(audio_payload)
            await _send_event(websocket, "server.hr_opening", payload)
            logger.info("hr_opening session_id=%s len=%s", session_id, len(opening))
        except Exception as exc:
            logger.exception("hr_opening_failed session_id=%s error=%s", session_id, exc)
            await _send_event(
                websocket,
                "server.hr_opening",
                {"text": opening, "session_id": session_id, "tts_error": str(exc)},
            )
        await emit_call_state("listening")

    def sync_emit_hr_delta(chunk: str) -> None:
        nonlocal first_hr_delta_at
        if not chunk:
            return
        if first_hr_delta_at is None:
            first_hr_delta_at = time.perf_counter()
            if _latency_enabled() and turn_started_at is not None:
                logger.info(
                    "latency llm_first_delta session_id=%s utterance_id=%s after_turn_start_ms=%.1f",
                    session_id,
                    utterance_id,
                    (first_hr_delta_at - turn_started_at) * 1000,
                )
        fut = asyncio.run_coroutine_threadsafe(emit_hr_delta(chunk), loop)
        emit_futures.append(fut)

    async def await_pending_emits() -> None:
        if not emit_futures:
            return
        pending = list(emit_futures)
        emit_futures.clear()
        for fut in pending:
            try:
                fut.result(timeout=60)
            except Exception as exc:
                logger.warning("emit_hr_delta pending failed session_id=%s error=%s", session_id, exc)

    async def emit_asr_partial(text: str) -> None:
        nonlocal asr_first_partial_at
        if _latency_enabled():
            now = time.perf_counter()
            if asr_first_partial_at is None:
                asr_first_partial_at = now
                if utterance_started_at is not None:
                    logger.info(
                        "latency asr_first_partial session_id=%s utterance_id=%s after_speech_start_ms=%.1f text_len=%s",
                        session_id,
                        utterance_id,
                        (now - utterance_started_at) * 1000,
                        len(text),
                    )
        await _send_event(websocket, "server.asr_partial", {"text": text})

    await _send_event(
        websocket,
        "server.conn_ready",
        {
            "session_id": session_id,
            "capabilities": {
                "voice_chunk": True,
                "asr_partial": True,
                "asr_final": True,
                "hr_stream": True,
                "hr_tts_stream": _tts_enabled(),
                "turn_done": True,
                "barge_in": True,
                "call_state": True,
                "hr_opening": True,
            },
        },
    )
    await emit_hr_opening()

    try:
        while True:
            raw = await websocket.receive_text()
            data = _safe_json(raw)
            event_type = str(data.get("type", "")).strip()
            payload = data.get("payload", {}) if isinstance(data.get("payload"), dict) else {}
            if event_type == "client.session_init":
                await _send_event(websocket, "server.conn_ready", {"session_id": session_id, "ok": True})
                continue
            if event_type == "client.hangup":
                await _send_event(websocket, "server.turn_done", {"session": session.model_dump(), "closed": True})
                await websocket.close()
                return
            if event_type == "client.barge_in":
                logger.info("barge_in session_id=%s", session_id)
                await _send_event(websocket, "server.barge_in_ack", {"session_id": session_id})
                continue
            if event_type == "client.reset_utterance":
                utterance_id += 1
                utterance_started_at = time.perf_counter()
                utterance_first_chunk_at = None
                utterance_bytes = 0
                voice_chunk_count = 0
                asr_first_partial_at = None
                commit_called_at = None
                turn_started_at = None
                first_hr_delta_at = None
                first_tts_audio_at = None
                if _latency_enabled():
                    logger.info("latency utterance_start session_id=%s utterance_id=%s", session_id, utterance_id)
                voice_service.reset()
                if asr_session is not None:
                    await asr_session.close()
                    asr_session = None
                continue
            if event_type == "client.voice_chunk":
                chunk_b64 = str(payload.get("chunk_b64", "")).strip()
                if chunk_b64:
                    voice_chunk_count += 1
                    if _asr_provider() == "bailian":
                        if asr_session is None:
                            asr_session = BailianRealtimeAsrSession(on_partial=emit_asr_partial)
                        try:
                            t0 = time.perf_counter()
                            audio_bytes = base64.b64decode(chunk_b64)
                            utterance_bytes += len(audio_bytes)
                            if utterance_first_chunk_at is None:
                                utterance_first_chunk_at = time.perf_counter()
                                if _latency_enabled() and utterance_started_at is not None:
                                    logger.info(
                                        "latency first_voice_chunk session_id=%s utterance_id=%s after_start_ms=%.1f bytes=%s",
                                        session_id,
                                        utterance_id,
                                        (utterance_first_chunk_at - utterance_started_at) * 1000,
                                        len(audio_bytes),
                                    )
                            await asr_session.send_audio(audio_bytes)
                            if _latency_enabled() and voice_chunk_count % 10 == 0:
                                t1 = time.perf_counter()
                                logger.info(
                                    "latency voice_chunk_forward session_id=%s utterance_id=%s chunk=%s forward_ms=%.1f total_bytes=%s",
                                    session_id,
                                    utterance_id,
                                    voice_chunk_count,
                                    (t1 - t0) * 1000,
                                    utterance_bytes,
                                )
                        except BailianAsrError as exc:
                            await _send_event(
                                websocket,
                                "server.error",
                                {"code": "asr_failed", "message": str(exc)},
                            )
                            await emit_call_state("listening")
                        except Exception:
                            await _send_event(
                                websocket,
                                "server.error",
                                {"code": "asr_failed", "message": "asr error"},
                            )
                            await emit_call_state("listening")
                    else:
                        voice_service.append_chunk_base64(chunk_b64)
                        if voice_service.chunk_count == 1 or voice_service.chunk_count % 5 == 0:
                            logger.info(
                                "voice_chunk session_id=%s count=%s bytes=%s",
                                session_id,
                                voice_service.chunk_count,
                                voice_service.received_bytes,
                            )
                        await _send_event(
                            websocket,
                            "server.asr_partial",
                            {
                                "text": f"正在识别...已接收{voice_service.chunk_count}段音频",
                                "received_bytes": voice_service.received_bytes,
                            },
                        )
                continue
            if event_type == "client.user_text":
                player_text = str(payload.get("text", "")).strip()
                if not player_text:
                    await _send_event(websocket, "server.error", {"message": "empty user text"})
                    continue
                emit_futures.clear()
                hr_speaking_sent = False
                tts_buffer = ""
                turn_started_at = time.perf_counter()
                first_hr_delta_at = None
                first_tts_audio_at = None
                await emit_call_state("thinking")
                next_state, result, flow = await asyncio.to_thread(
                    orchestrator.run_realtime_text_turn,
                    session,
                    player_text,
                    sync_emit_hr_delta,
                )
                if _latency_enabled():
                    logger.info(
                        "latency llm_turn_done session_id=%s utterance_id=%s ms=%.1f user_text_len=%s",
                        session_id,
                        utterance_id,
                        (time.perf_counter() - turn_started_at) * 1000,
                        len(player_text),
                    )
                await await_pending_emits()
                if not _ws_connected(websocket):
                    session = next_state
                    SESSIONS[session_id] = next_state
                    voice_service.reset()
                    continue
                if _tts_enabled() and _tts_mode() == "backend" and tts_buffer.strip():
                    seq += 1
                    sid = resolve_tts_speaker_id(session.hr_personality_id)
                    audio_payload = synthesize_wav_base64(tts_buffer, speaker_id=sid)
                    if not hr_speaking_sent:
                        hr_speaking_sent = True
                        await emit_call_state("speaking")
                    await _send_event(
                        websocket,
                        "server.hr_audio_chunk",
                        {**audio_payload, "text": tts_buffer, "session_id": session_id},
                        seq=seq,
                    )
                    tts_buffer = ""
                session = next_state
                SESSIONS[session_id] = next_state
                await emit_call_state("listening")
                await _send_event(
                    websocket,
                    "server.turn_done",
                    {"result": result.model_dump(), "session": next_state.model_dump(), "flow": flow.model_dump()},
                )
                continue
            if event_type == "client.commit_utterance":
                mime_type = str(payload.get("mime_type", "audio/wav"))
                commit_called_at = time.perf_counter()
                logger.info(
                    "commit_utterance session_id=%s chunks=%s bytes=%s mime=%s",
                    session_id,
                    voice_service.chunk_count,
                    voice_service.received_bytes,
                    mime_type,
                )
                transcript = ""
                confidence = 0.0
                if _asr_provider() == "bailian":
                    if asr_session is None:
                        await _send_event(
                            websocket,
                            "server.asr_skipped",
                            {"reason": "empty", "message": "未收到音频数据"},
                        )
                        voice_service.reset()
                        await emit_call_state("listening")
                        continue
                    if _latency_enabled() and utterance_started_at is not None:
                        logger.info(
                            "latency commit session_id=%s utterance_id=%s after_start_ms=%.1f bytes=%s chunks=%s",
                            session_id,
                            utterance_id,
                            (commit_called_at - utterance_started_at) * 1000,
                            utterance_bytes,
                            voice_chunk_count,
                        )
                    transcript = await asr_session.finish_and_get_final(timeout=10.0)
                    confidence = 0.9 if transcript else 0.0
                    await asr_session.close()
                    asr_session = None
                else:
                    if voice_service.received_bytes <= 0:
                        await _send_event(
                            websocket,
                            "server.asr_skipped",
                            {"reason": "empty", "message": "未收到音频数据"},
                        )
                        voice_service.reset()
                        await emit_call_state("listening")
                        continue
                    try:
                        asr = voice_service.transcribe_current_audio(mime_type=mime_type)
                    except AsrPipelineError as exc:
                        await _send_event(
                            websocket,
                            "server.error",
                            {"code": "asr_failed", "message": str(exc)},
                        )
                        voice_service.reset()
                        await emit_call_state("listening")
                        continue
                    transcript = str(asr.get("transcript", "")).strip()
                    confidence = float(asr.get("confidence", 0.0)) if transcript else 0.0
                await _send_event(
                    websocket,
                    "server.asr_final",
                    {"transcript": transcript, "confidence": confidence},
                )
                if not transcript:
                    await _send_event(
                        websocket,
                        "server.asr_skipped",
                        {"reason": "empty", "message": "未识别到语音"},
                    )
                    voice_service.reset()
                    await emit_call_state("listening")
                    continue
                emit_futures.clear()
                hr_speaking_sent = False
                tts_buffer = ""
                turn_started_at = time.perf_counter()
                first_hr_delta_at = None
                first_tts_audio_at = None
                await emit_call_state("thinking")
                next_state, voice_result, flow = await asyncio.to_thread(
                    orchestrator.run_realtime_voice_turn,
                    session,
                    transcript,
                    confidence,
                    sync_emit_hr_delta,
                )
                if _latency_enabled():
                    logger.info(
                        "latency llm_turn_done session_id=%s utterance_id=%s ms=%.1f asr_len=%s",
                        session_id,
                        utterance_id,
                        (time.perf_counter() - turn_started_at) * 1000,
                        len(transcript),
                    )
                await await_pending_emits()
                if not _ws_connected(websocket):
                    session = next_state
                    SESSIONS[session_id] = next_state
                    voice_service.reset()
                    continue
                if _tts_enabled() and _tts_mode() == "backend" and tts_buffer.strip():
                    seq += 1
                    sid = resolve_tts_speaker_id(session.hr_personality_id)
                    audio_payload = synthesize_wav_base64(tts_buffer, speaker_id=sid)
                    if not hr_speaking_sent:
                        hr_speaking_sent = True
                        await emit_call_state("speaking")
                    await _send_event(
                        websocket,
                        "server.hr_audio_chunk",
                        {**audio_payload, "text": tts_buffer, "session_id": session_id},
                        seq=seq,
                    )
                    tts_buffer = ""
                session = next_state
                SESSIONS[session_id] = next_state
                await emit_call_state("listening")
                await _send_event(
                    websocket,
                    "server.turn_done",
                    {
                        "asr": {"transcript": voice_result.asr_text, "confidence": voice_result.confidence},
                        "result": voice_result.turn_result.model_dump(),
                        "session": next_state.model_dump(),
                        "flow": flow.model_dump(),
                    },
                )
                voice_service.reset()
                continue
            await _send_event(websocket, "server.error", {"message": f"unsupported event type: {event_type}"})
    except WebSocketDisconnect:
        if asr_session is not None:
            await asr_session.close()
        return
    except Exception as exc:
        if asr_session is not None:
            await asr_session.close()
        logger.exception("ws_session_error session_id=%s", session_id)
        await _send_event(websocket, "server.error", {"message": str(exc)})
        if _ws_connected(websocket):
            try:
                await websocket.close(code=1011)
            except Exception:
                pass
        return


def _safe_json(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _ws_enabled() -> bool:
    value = os.getenv("REALTIME_WS_ENABLED", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _asr_provider() -> str:
    value = os.getenv("REALTIME_ASR_PROVIDER", "").strip().lower()
    if value in {"bailian", "dashscope", "paraformer"}:
        return "bailian"
    if value in {"offline", "sherpa", "local"}:
        return "offline"
    if os.getenv("DASHSCOPE_API_KEY", "").strip():
        return "bailian"
    return "offline"


def _latency_enabled() -> bool:
    value = os.getenv("REALTIME_LATENCY_LOG", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _tts_enabled() -> bool:
    value = os.getenv("REALTIME_TTS_ENABLED", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _tts_mode() -> str:
    value = os.getenv("REALTIME_TTS_MODE", "browser").strip().lower()
    if value in {"backend", "server"}:
        return "backend"
    return "browser"


def _should_flush_tts(buffer_text: str, last_chunk: str) -> bool:
    chunk = (last_chunk or "").strip()
    if not chunk:
        return False
    if any(p in chunk for p in ("。", "！", "？", ".", "!", "?", "，", ",", "、", "；", ";")):
        return True
    return len(buffer_text) >= 18


def _ws_connected(websocket: WebSocket) -> bool:
    return websocket.client_state == WebSocketState.CONNECTED


async def _send_event(websocket: WebSocket, event_type: str, payload: dict[str, Any], seq: int | None = None) -> bool:
    if not _ws_connected(websocket):
        return False
    body = {
        "type": event_type,
        "payload": payload,
        "ts": int(time.time() * 1000),
    }
    if seq is not None:
        body["seq"] = seq
    try:
        await websocket.send_json(body)
        return True
    except WebSocketDisconnect:
        return False
    except RuntimeError as exc:
        if "close message has been sent" in str(exc).lower():
            return False
        raise
