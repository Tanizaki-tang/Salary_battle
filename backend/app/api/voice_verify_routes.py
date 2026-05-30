from __future__ import annotations

from fastapi import APIRouter

from app.modules.voice_battle.voice_diagnostics import run_voice_diagnostics
from app.shared_types.game_types import ApiResponse


router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


@router.get("/verify")
def verify_voice_pipeline() -> ApiResponse:
    return ApiResponse(data=run_voice_diagnostics())
