from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.api.session_routes import SESSIONS, orchestrator
from app.modules.voice_battle.speech_gateway import AsrPipelineError, transcribe_file
from app.modules.voice_battle.voice_diagnostics import run_voice_diagnostics
from app.shared_types.game_types import ApiResponse


router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


@router.get("/verify")
def verify_voice_pipeline() -> ApiResponse:
    return ApiResponse(data=run_voice_diagnostics())


@router.post("/verify-realtime")
async def verify_realtime_voice(
    audio_file: UploadFile = File(...),
    session_id: str | None = Query(default=None),
) -> ApiResponse:
    started = time.perf_counter()
    raw = await audio_file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="empty audio file")

    mime_type = (audio_file.content_type or "application/octet-stream").strip()
    suffix = Path(audio_file.filename or "").suffix or (".wav" if "wav" in mime_type else ".webm")
    tmp_path = ""
    convert_ms = 0
    asr_ms = 0
    try:
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="salary_battle_verify_") as tmp:
            tmp_path = tmp.name
            tmp.write(raw)

        convert_started = time.perf_counter()
        asr_started = time.perf_counter()
        try:
            asr = transcribe_file(tmp_path, mime_type=mime_type)
        except AsrPipelineError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        asr_ms = int((time.perf_counter() - asr_started) * 1000)
        convert_ms = int((asr_started - convert_started) * 1000)

        transcript = str(asr.get("transcript", "")).strip()
        confidence = float(asr.get("confidence", 0.0))
        total_ms = int((time.perf_counter() - started) * 1000)

        payload: dict = {
            "ok": bool(transcript),
            "asr": {"transcript": transcript, "confidence": confidence},
            "timing": {"convert_ms": convert_ms, "asr_ms": asr_ms, "total_ms": total_ms},
            "input_mime": mime_type,
            "error": None if transcript else "empty_transcript",
        }

        if session_id and transcript:
            session = SESSIONS.get(session_id)
            if session is None:
                payload["agent_preview"] = {"skipped": True, "reason": "session_not_found"}
            else:
                next_state, voice_result, flow = orchestrator.run_realtime_voice_turn(
                    session, transcript, confidence
                )
                SESSIONS[session_id] = next_state
                payload["agent_preview"] = {
                    "hr_reply": voice_result.turn_result.hr_reply,
                    "flow": flow.model_dump(),
                    "session_round": next_state.round_index,
                }

        return ApiResponse(data=payload)
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
