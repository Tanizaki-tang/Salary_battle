from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


StrategyType = Literal["strong_push", "probe", "concede", "counter_pressure"]


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: dict = Field(default_factory=dict)


class SessionState(BaseModel):
    session_id: str
    user_id: str
    status: Literal["ongoing", "settled", "closed"] = "ongoing"
    round_index: int = 1
    max_round: int = 5
    hr_patience: int = 70
    info_exposure: int = 20
    trap_count: int = 0


class TextTurnPayload(BaseModel):
    strategy: Optional[StrategyType] = None
    player_text: Optional[str] = None


class VoiceTurnPayload(BaseModel):
    audio_path: str
    input_mode: str = "voice"


class TurnDelta(BaseModel):
    hr_patience: int
    info_exposure: int
    trap_count: int


class TurnResult(BaseModel):
    hr_reply: str
    delta: TurnDelta
    is_trap_hit: bool
    is_game_over: bool
    next_round: int


class VoiceTurnResult(BaseModel):
    asr_text: str
    confidence: float
    turn_result: TurnResult


class SettleResult(BaseModel):
    final_salary: int
    final_score: int
    grade: str
    review_tip: str


class PersistResult(BaseModel):
    saved: bool
    user_id: str
    session_id: str
