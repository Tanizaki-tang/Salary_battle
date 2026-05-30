from __future__ import annotations

import tempfile
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.modules.voice_battle.speech_gateway import SpeechRecognitionError
from app.modules.voice_battle.tts_gateway import tts_output_dir
from app.orchestrators.game_flow_orchestrator import GameFlowOrchestrator
from app.shared_types.game_types import ApiResponse, SessionState, TextTurnPayload, VoiceTurnPayload


router = APIRouter(prefix="/api/v1", tags=["game"])
orchestrator = GameFlowOrchestrator()
SESSIONS: dict[str, SessionState] = {}
SUPPORTED_AUDIO_SUFFIXES = {".wav", ".mp3", ".m4a", ".webm"}


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

    audio_path = await _save_upload_audio(audio_file)
    try:
        voice_payload = VoiceTurnPayload(audio_path=str(audio_path))
        next_state, voice_result = await orchestrator.run_voice_turn_with_tts(session, voice_payload)
        if voice_result.hr_audio_path:
            voice_result.hr_audio_url = f"/api/v1/speech/tts/{Path(voice_result.hr_audio_path).name}"
        SESSIONS[session_id] = next_state
        return ApiResponse(
            data={
                "asr": {"transcript": voice_result.asr_text, "confidence": voice_result.confidence},
                "result": voice_result.turn_result.model_dump(),
                "tts": {
                    "audio_url": voice_result.hr_audio_url,
                    "voice": voice_result.tts_voice,
                    "error": voice_result.tts_error,
                },
                "session": next_state.model_dump(),
            }
        )
    except SpeechRecognitionError as exc:
        return ApiResponse(
            code=5002,
            message="ASR failed, please retry or use text-turn",
            data={"hint": str(exc)},
        )
    finally:
        audio_path.unlink(missing_ok=True)


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
    audio_path = await _save_upload_audio(audio_file)
    try:
        result = orchestrator.voice_engine.transcribe_only(VoiceTurnPayload(audio_path=str(audio_path)))
        return ApiResponse(data={**result, "file": audio_file.filename})
    except SpeechRecognitionError as exc:
        return ApiResponse(
            code=5002,
            message="ASR failed, please retry or use text-turn",
            data={"hint": str(exc)},
        )
    finally:
        audio_path.unlink(missing_ok=True)


@router.get("/speech/tts/{filename}")
def tts_audio(filename: str) -> FileResponse:
    audio_path = tts_output_dir() / filename
    if not audio_path.is_file() or audio_path.suffix.lower() != ".mp3":
        raise HTTPException(status_code=404, detail="tts audio not found")
    return FileResponse(path=audio_path, media_type="audio/mpeg", filename=filename)


async def _save_upload_audio(audio_file: UploadFile) -> Path:
    suffix = Path(audio_file.filename or "").suffix.lower()
    if suffix not in SUPPORTED_AUDIO_SUFFIXES:
        raise HTTPException(status_code=400, detail="audio_file must be wav/mp3/m4a/webm")

    with tempfile.NamedTemporaryFile(prefix="salary_battle_upload_", suffix=suffix, delete=False) as tmp:
        audio_path = Path(tmp.name)
        tmp.write(await audio_file.read())
    return audio_path
