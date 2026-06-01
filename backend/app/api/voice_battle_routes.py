from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.api.session_routes import create_session_data, orchestrator
from app.modules.voice_battle.dashscope_realtime_asr import DashScopeRealtimeAsr
from app.modules.voice_battle.qwen_tts_realtime_gateway import QwenTtsRealtimeSession
from app.modules.voice_battle.sherpa_streaming_asr import SherpaStreamingAsr
from app.repositories.session_repository import get_text_session, save_text_session
from app.service.runtime_auth import RuntimeAuth, require_runtime_auth, resolve_runtime_auth, runtime_auth_scope
from app.shared_types.game_types import ApiResponse, SessionState, TextTurnPayload


router = APIRouter(prefix="/api/v1", tags=["voice-battle"])
logger = logging.getLogger(__name__)
HARD_TTS_BREAKS = "。！？!?；;\n"
SOFT_TTS_BREAKS = "，,、"


def _prefer_cloud_asr() -> bool:
    raw = (os.getenv("VOICE_BATTLE_ASR_PROVIDER") or "").strip().lower()
    if raw in {"cloud", "dashscope", "qwen"}:
        return True
    if raw in {"local", "sherpa"}:
        return False
    return True


def _pick_tts_flush_index(text: str, *, force: bool = False) -> int:
    last_hard = max((text.rfind(ch) for ch in HARD_TTS_BREAKS), default=-1)
    if last_hard >= 0:
        return last_hard + 1
    if len(text) >= 28:
        last_soft = max((text.rfind(ch) for ch in SOFT_TTS_BREAKS), default=-1)
        if last_soft >= 12:
            return last_soft + 1
    if force and text.strip():
        return len(text)
    if len(text) >= 40:
        return 24
    return 0


def _drain_tts_segments(buffer: str, *, force: bool = False) -> tuple[list[str], str]:
    text = buffer
    segments: list[str] = []
    while text:
        cut = _pick_tts_flush_index(text, force=force)
        if cut <= 0:
            break
        segment = text[:cut].strip()
        if segment:
            segments.append(segment)
        text = text[cut:].lstrip()
        force = force and bool(text)
    return segments, text


def _clamp_unit(value: Any, fallback: float = 0.5) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(0.0, min(1.0, numeric))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@router.post("/voice-battle/sessions")
def create_voice_session(payload: dict, auth: RuntimeAuth = Depends(require_runtime_auth)) -> ApiResponse:
    with runtime_auth_scope(auth):
        voice_payload = dict(payload)
        voice_payload["interaction_mode"] = "voice"
        return ApiResponse(data=create_session_data(voice_payload, max_round_override=50))


@router.websocket("/voice-battle/ws/{session_id}")
async def voice_battle_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        auth_msg = await websocket.receive_json()
    except Exception:
        await websocket.send_text(json.dumps({"type": "error", "message": "missing auth payload"}, ensure_ascii=False))
        await websocket.close(code=1008)
        return

    if auth_msg.get("type") != "auth":
        await websocket.send_text(json.dumps({"type": "error", "message": "auth required"}, ensure_ascii=False))
        await websocket.close(code=1008)
        return

    try:
        auth = resolve_runtime_auth(
            str(auth_msg.get("api_key") or ""),
            str(auth_msg.get("debug_password") or ""),
        )
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        await websocket.send_text(json.dumps({"type": "error", "message": str(detail)}, ensure_ascii=False))
        await websocket.close(code=1008)
        return

    asr_sensitivity = _clamp_unit(auth_msg.get("asr_sensitivity"), 0.5)
    vad_threshold = _lerp(0.8, 0.0, asr_sensitivity)
    silence_ms = int(_lerp(700.0, 250.0, asr_sensitivity))

    session = get_text_session(session_id)
    if not session:
        await websocket.send_text(json.dumps({"type": "error", "message": "session not found"}, ensure_ascii=False))
        await websocket.close(code=1008)
        return

    try:
        with runtime_auth_scope(auth):
            if _prefer_cloud_asr():
                asr = DashScopeRealtimeAsr(loop=asyncio.get_running_loop(), vad_threshold=vad_threshold, silence_ms=silence_ms)
                await asyncio.to_thread(asr.connect)
            else:
                asr = SherpaStreamingAsr(
                    rule1_min_trailing_silence=_lerp(3.0, 1.2, asr_sensitivity),
                    rule2_min_trailing_silence=_lerp(1.6, 0.7, asr_sensitivity),
                )
    except Exception as exc:
        await websocket.send_text(json.dumps({"type": "error", "message": f"ASR init failed: {exc}"}, ensure_ascii=False))
        await websocket.close(code=1011)
        return

    await websocket.send_text(json.dumps({"type": "ready", "asr": asr.debug_info()}, ensure_ascii=False))

    loop = asyncio.get_running_loop()
    last_partial = ""

    async def run_hr_turn(final_text: str) -> None:
        nonlocal session
        tts_events: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

        def on_tts_event(evt: dict[str, Any]) -> None:
            tts_events.put_nowait(evt)

        with runtime_auth_scope(auth):
            tts = QwenTtsRealtimeSession(loop=loop, on_event=on_tts_event)

        def _connect() -> None:
            with runtime_auth_scope(auth):
                tts.connect()

        await asyncio.to_thread(_connect)

        async def forward_tts_events() -> None:
            while True:
                evt = await tts_events.get()
                t = (evt.get("type") or "").strip()
                if t == "response.audio.delta":
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "hr.audio.delta",
                                "audio_b64": evt.get("delta"),
                                "format": "pcm_s16le",
                                "sample_rate": 24000,
                            },
                            ensure_ascii=False,
                        )
                    )
                elif t in {"response.done"}:
                    await websocket.send_text(json.dumps({"type": "hr.audio.done"}, ensure_ascii=False))
                elif t in {"session.finished"}:
                    await websocket.send_text(json.dumps({"type": "hr.audio.session_finished"}, ensure_ascii=False))
                    break

        forward_task = asyncio.create_task(forward_tts_events())

        payload = TextTurnPayload(player_text=final_text)
        hr_text_parts: list[str] = []
        tts_buffer = ""

        def _append_tts(segment: str) -> None:
            with runtime_auth_scope(auth):
                tts.append_text(segment)

        def _finish_tts() -> None:
            with runtime_auth_scope(auth):
                tts.finish()

        def _wait_tts_closed() -> None:
            with runtime_auth_scope(auth):
                tts.wait_closed()

        try:
            await websocket.send_text(json.dumps({"type": "hr.text.start"}, ensure_ascii=False))
            with runtime_auth_scope(auth):
                for evt in orchestrator.iter_text_turn(session, payload):
                    if evt.get("event") == "token":
                        text = str(evt.get("text") or "")
                        hr_text_parts.append(text)
                        await websocket.send_text(json.dumps({"type": "hr.text.delta", "text": text}, ensure_ascii=False))
                        tts_buffer += text
                        segments, tts_buffer = _drain_tts_segments(tts_buffer)
                        for segment in segments:
                            await asyncio.to_thread(_append_tts, segment)
                    elif evt.get("event") == "done":
                        segments, tts_buffer = _drain_tts_segments(tts_buffer, force=True)
                        for segment in segments:
                            await asyncio.to_thread(_append_tts, segment)
                        session = SessionState.model_validate(evt["session"])
                        save_text_session(session)
                        await websocket.send_text(
                            json.dumps(
                                {"type": "hr.text.done", "text": "".join(hr_text_parts)},
                                ensure_ascii=False,
                            )
                        )
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "turn.done",
                                    "result": evt["result"],
                                    "session": evt["session"],
                                    "flow": evt["flow"],
                                    "hr_text": "".join(hr_text_parts),
                                },
                                ensure_ascii=False,
                            )
                        )
        except Exception as exc:
            logger.exception("VOICE_BATTLE_TURN_FAILED session_id=%s", session_id)
            await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False))
        finally:
            await asyncio.to_thread(_finish_tts)
            await asyncio.to_thread(_wait_tts_closed)
            await forward_task

    try:
        while True:
            msg = await websocket.receive()
            if "text" in msg and msg["text"] is not None:
                try:
                    data = json.loads(msg["text"])
                except Exception:
                    await websocket.send_text(json.dumps({"type": "error", "message": "invalid json"}, ensure_ascii=False))
                    continue
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}, ensure_ascii=False))
                continue

            if "bytes" in msg and msg["bytes"] is not None:
                if isinstance(asr, DashScopeRealtimeAsr):
                    await asyncio.to_thread(asr.append_audio, msg["bytes"])
                    for r in asr.drain_results():
                        if r.is_final:
                            if r.final_text.strip():
                                await websocket.send_text(
                                    json.dumps({"type": "asr.final", "text": r.final_text}, ensure_ascii=False)
                                )
                                await run_hr_turn(r.final_text)
                            last_partial = ""
                        else:
                            if r.partial != last_partial and r.partial:
                                last_partial = r.partial
                                await websocket.send_text(
                                    json.dumps({"type": "asr.partial", "text": r.partial}, ensure_ascii=False)
                                )
                else:
                    r = asr.accept_pcm16le(msg["bytes"], sample_rate=asr.sample_rate)
                    if r.is_final:
                        if r.final_text.strip():
                            await websocket.send_text(json.dumps({"type": "asr.final", "text": r.final_text}, ensure_ascii=False))
                            await run_hr_turn(r.final_text)
                        last_partial = ""
                    else:
                        if r.partial != last_partial and r.partial:
                            last_partial = r.partial
                            await websocket.send_text(json.dumps({"type": "asr.partial", "text": r.partial}, ensure_ascii=False))
                continue
    except WebSocketDisconnect:
        return
    finally:
        if isinstance(asr, DashScopeRealtimeAsr):
            await asyncio.to_thread(asr.close)
