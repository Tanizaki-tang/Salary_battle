from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.orchestrators.game_flow_orchestrator import GameFlowOrchestrator
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
    session = SessionState(session_id=f"sess_{uuid4().hex[:8]}", user_id=user_id)
    SESSIONS[session.session_id] = session
    return ApiResponse(data={"session": session.model_dump(), "hr_opening": "你好，我们这边给你的总包是 12k*14，你怎么看？"})


@router.post("/sessions/{session_id}/text-turn")
def text_turn(session_id: str, payload: TextTurnPayload) -> ApiResponse:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    next_state, turn_result = orchestrator.run_text_turn(session, payload)
    SESSIONS[session_id] = next_state
    return ApiResponse(data={"result": turn_result.model_dump(), "session": next_state.model_dump()})


@router.post("/sessions/{session_id}/voice-turn")
async def voice_turn(session_id: str, audio_file: UploadFile = File(...)) -> ApiResponse:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    voice_payload = VoiceTurnPayload(audio_path=audio_file.filename or "unknown.wav")
    next_state, voice_result = orchestrator.run_voice_turn(session, voice_payload)
    SESSIONS[session_id] = next_state
    return ApiResponse(
        data={
            "asr": {"transcript": voice_result.asr_text, "confidence": voice_result.confidence},
            "result": voice_result.turn_result.model_dump(),
            "session": next_state.model_dump(),
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
    return ApiResponse(data={"transcript": "我想确认一下试用期薪资和转正后的基数。", "confidence": 0.9, "file": audio_file.filename})
