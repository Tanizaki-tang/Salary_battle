from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.orchestrators.game_flow_orchestrator import GameFlowOrchestrator
from app.modules.voice_battle.speech_gateway import transcribe_audio
from app.repositories.scene_repository import load_scene, resolve_scene_id
from app.shared_types.game_types import ApiResponse, SessionState, TextTurnPayload, VoiceTurnPayload


router = APIRouter(prefix="/api/v1", tags=["game"])
orchestrator = GameFlowOrchestrator()
SESSIONS: dict[str, SessionState] = {}


@router.get("/health")
def health() -> ApiResponse:
    return ApiResponse(data={"status": "healthy", "service": "salary-battle-api", "version": "v1.2"})


@router.post("/sessions")
def create_session(payload: dict) -> ApiResponse:
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    user_name = (payload.get("user_name") or "").strip() or "候选人"
    scene_id = resolve_scene_id(scene_id=payload.get("scene_id"), role_id=payload.get("role_id"))
    role_id = payload.get("role_id") or "role_backend"
    scene_context = load_scene(scene_id)
    initial = scene_context.initial_state
    session = SessionState(
        session_id=f"sess_{uuid4().hex[:8]}",
        user_id=user_id,
        user_name=user_name,
        role_id=role_id,
        scene_id=scene_id,
        max_round=initial.max_round,
        hr_patience=initial.hr_patience,
        info_exposure=initial.info_exposure,
        trap_count=initial.trap_count,
        current_salary_offer=scene_context.salary_anchor.hr_initial_offer,
        scene_context=scene_context,
    )
    SESSIONS[session.session_id] = session
    return ApiResponse(
        data={
            "session": session.model_dump(),
            "hr_opening": f"{user_name}，{scene_context.opening_line}",
            "scene_meta": scene_context.meta.model_dump(),
        }
    )


@router.post("/sessions/{session_id}/text-turn")
def text_turn(session_id: str, payload: TextTurnPayload) -> ApiResponse:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    next_state, turn_result, flow = orchestrator.run_text_turn(session, payload)
    SESSIONS[session_id] = next_state
    return ApiResponse(data={"result": turn_result.model_dump(), "session": next_state.model_dump(), "flow": flow.model_dump()})


@router.post("/sessions/{session_id}/voice-turn")
async def voice_turn(session_id: str, audio_file: UploadFile = File(...)) -> ApiResponse:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    suffix = Path(audio_file.filename or "").suffix or ".wav"
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="salary_battle_audio_") as tmp:
            tmp_path = tmp.name
            tmp.write(await audio_file.read())
        voice_payload = VoiceTurnPayload(audio_path=tmp_path)
        next_state, voice_result, flow = orchestrator.run_voice_turn(session, voice_payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    SESSIONS[session_id] = next_state
    return ApiResponse(
        data={
            "asr": {"transcript": voice_result.asr_text, "confidence": voice_result.confidence},
            "result": voice_result.turn_result.model_dump(),
            "session": next_state.model_dump(),
            "flow": flow.model_dump(),
        }
    )


@router.post("/sessions/{session_id}/settle")
def settle(session_id: str) -> ApiResponse:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    settle_result, persist_result = orchestrator.settle_and_persist(session)
    session.status = "settled"
    SESSIONS[session_id] = session
    return ApiResponse(data={"result": settle_result.model_dump(), "persist": persist_result.model_dump()})


@router.post("/speech/asr")
async def asr(audio_file: UploadFile = File(...)) -> ApiResponse:
    suffix = Path(audio_file.filename or "").suffix or ".wav"
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="salary_battle_asr_") as tmp:
            tmp_path = tmp.name
            tmp.write(await audio_file.read())
        asr_result = transcribe_audio(VoiceTurnPayload(audio_path=tmp_path))
        return ApiResponse(data={**asr_result, "file": audio_file.filename})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
