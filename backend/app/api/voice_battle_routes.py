from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.session_routes import SESSIONS, create_session_data, orchestrator
from app.modules.voice_battle.dashscope_realtime_asr import DashScopeRealtimeAsr
from app.modules.voice_battle.qwen_tts_realtime_gateway import QwenTtsRealtimeSession
from app.modules.voice_battle.sherpa_streaming_asr import SherpaStreamingAsr
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


@router.post("/voice-battle/sessions")
def create_voice_session(payload: dict) -> ApiResponse:
    return ApiResponse(data=create_session_data(payload, max_round_override=50))


@router.websocket("/voice-battle/ws/{session_id}")
async def voice_battle_ws(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    session = SESSIONS.get(session_id)
    if not session:
        await websocket.send_text(json.dumps({"type": "error", "message": "session not found"}, ensure_ascii=False))
        await websocket.close(code=1008)
        return

    try:
        if _prefer_cloud_asr():
            asr = DashScopeRealtimeAsr(loop=asyncio.get_running_loop())
            await asyncio.to_thread(asr.connect)
        else:
            asr = SherpaStreamingAsr()
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

        tts = QwenTtsRealtimeSession(loop=loop, on_event=on_tts_event)

        def _connect() -> None:
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
        try:
            await websocket.send_text(json.dumps({"type": "hr.text.start"}, ensure_ascii=False))
            for evt in orchestrator.iter_text_turn(session, payload):
                if evt.get("event") == "token":
                    text = str(evt.get("text") or "")
                    hr_text_parts.append(text)
                    await websocket.send_text(json.dumps({"type": "hr.text.delta", "text": text}, ensure_ascii=False))
                    tts_buffer += text
                    segments, tts_buffer = _drain_tts_segments(tts_buffer)
                    for segment in segments:
                        await asyncio.to_thread(tts.append_text, segment)
                elif evt.get("event") == "done":
                    segments, tts_buffer = _drain_tts_segments(tts_buffer, force=True)
                    for segment in segments:
                        await asyncio.to_thread(tts.append_text, segment)
                    session = SessionState.model_validate(evt["session"])
                    SESSIONS[session_id] = session
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
            await asyncio.to_thread(tts.finish)
            await asyncio.to_thread(tts.wait_closed)
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
