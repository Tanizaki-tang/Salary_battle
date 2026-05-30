from __future__ import annotations

import json
import os
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.session_routes import SESSIONS, orchestrator
from app.modules.voice_battle.realtime_voice_service import RealtimeVoiceService
from app.modules.voice_battle.speech_gateway import AsrPipelineError
from app.modules.voice_battle.tts_gateway import synthesize_wav_base64

WS_PATH = "/api/v1/ws/sessions/{session_id}"

router = APIRouter(tags=["realtime"])


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
    seq = 0
    tts_buffer = ""

    async def emit_hr_delta(chunk: str) -> None:
        nonlocal seq
        nonlocal tts_buffer
        seq += 1
        await _send_event(websocket, "server.hr_delta", {"delta": chunk, "session_id": session_id}, seq=seq)
        if _tts_enabled():
            if _tts_mode() == "backend":
                tts_buffer += chunk
                if _should_flush_tts(tts_buffer, chunk):
                    audio_payload = synthesize_wav_base64(tts_buffer)
                    await _send_event(
                        websocket,
                        "server.hr_audio_chunk",
                        {**audio_payload, "text": tts_buffer, "session_id": session_id},
                        seq=seq,
                    )
                    tts_buffer = ""
            else:
                await _send_event(websocket, "server.hr_audio_chunk", {"text": chunk, "session_id": session_id}, seq=seq)

    def sync_emit_hr_delta(chunk: str) -> None:
        # WebSocket 回调上下文是同步函数，这里仅缓存，发送放在外层流程中批量完成。
        pending_deltas.append(chunk)

    pending_deltas: list[str] = []
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
            },
        },
    )

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
            if event_type == "client.voice_chunk":
                chunk_b64 = str(payload.get("chunk_b64", "")).strip()
                if chunk_b64:
                    voice_service.append_chunk_base64(chunk_b64)
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
                pending_deltas.clear()
                next_state, result, flow = orchestrator.run_realtime_text_turn(
                    session, player_text, on_delta=sync_emit_hr_delta
                )
                for piece in pending_deltas:
                    await emit_hr_delta(piece)
                if _tts_enabled() and _tts_mode() == "backend" and tts_buffer.strip():
                    seq += 1
                    audio_payload = synthesize_wav_base64(tts_buffer)
                    await _send_event(
                        websocket,
                        "server.hr_audio_chunk",
                        {**audio_payload, "text": tts_buffer, "session_id": session_id},
                        seq=seq,
                    )
                    tts_buffer = ""
                session = next_state
                SESSIONS[session_id] = next_state
                await _send_event(
                    websocket,
                    "server.turn_done",
                    {"result": result.model_dump(), "session": next_state.model_dump(), "flow": flow.model_dump()},
                )
                continue
            if event_type == "client.commit_utterance":
                mime_type = str(payload.get("mime_type", "audio/wav"))
                try:
                    asr = voice_service.transcribe_current_audio(mime_type=mime_type)
                except AsrPipelineError as exc:
                    await _send_event(
                        websocket,
                        "server.error",
                        {"code": "asr_failed", "message": str(exc)},
                    )
                    voice_service.reset()
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
                        "server.error",
                        {"code": "asr_empty", "message": "未识别到语音，请重试"},
                    )
                    voice_service.reset()
                    continue
                pending_deltas.clear()
                next_state, voice_result, flow = orchestrator.run_realtime_voice_turn(
                    session, transcript, confidence, on_delta=sync_emit_hr_delta
                )
                for piece in pending_deltas:
                    await emit_hr_delta(piece)
                if _tts_enabled() and _tts_mode() == "backend" and tts_buffer.strip():
                    seq += 1
                    audio_payload = synthesize_wav_base64(tts_buffer)
                    await _send_event(
                        websocket,
                        "server.hr_audio_chunk",
                        {**audio_payload, "text": tts_buffer, "session_id": session_id},
                        seq=seq,
                    )
                    tts_buffer = ""
                session = next_state
                SESSIONS[session_id] = next_state
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
        return
    except Exception as exc:
        await _send_event(websocket, "server.error", {"message": str(exc)})
        await websocket.close(code=1011)


def _safe_json(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _ws_enabled() -> bool:
    value = os.getenv("REALTIME_WS_ENABLED", "true").strip().lower()
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


async def _send_event(websocket: WebSocket, event_type: str, payload: dict[str, Any], seq: int | None = None) -> None:
    body = {
        "type": event_type,
        "payload": payload,
        "ts": int(time.time() * 1000),
    }
    if seq is not None:
        body["seq"] = seq
    await websocket.send_json(body)
