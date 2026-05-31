from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


StrategyType = Literal["strong_push", "probe", "concede", "counter_pressure"]
NextPhase = Literal["text", "end"]


class ApiResponse(BaseModel):
    code: int = 0
    message: str = "ok"
    data: dict = Field(default_factory=dict)


class TurnDelta(BaseModel):
    hr_patience: int
    info_exposure: int
    trap_count: int
    salary_offer: int = 0
    equity_ratio: float = 0.0
    law_citation_count: int = 0
    misjudge_count: int = 0


class SalaryAnchor(BaseModel):
    legal_floor: int
    market_fair: int
    ideal_target: int
    hr_initial_offer: int


class InitialState(BaseModel):
    max_round: int = 5
    hr_patience: int = 70
    info_exposure: int = 20
    trap_count: int = 0


class ScoreProfile(BaseModel):
    dq_weight: float = 0.35
    td_weight: float = 0.25
    wh_weight: float = 0.20
    si_weight: float = 0.20
    bonus_survival: int = 5
    bonus_strategy_diversity: int = 5
    penalty_high_exposure: int = 10
    high_exposure_threshold: int = 80
    grade_a: int = 85
    grade_b: int = 70


class SceneMeta(BaseModel):
    scene_id: str
    scene_name: str
    role_hint: str


class SceneContext(BaseModel):
    meta: SceneMeta
    opening_line: str
    initial_state: InitialState
    salary_anchor: SalaryAnchor
    score_profile: ScoreProfile
    tone_map: dict[StrategyType, str]
    strategy_delta_map: dict[StrategyType, TurnDelta]


class ConversationMessage(BaseModel):
    role: Literal["hr", "player", "system"] = "system"
    content: str
    round_index: int = 0


class SessionState(BaseModel):
    session_id: str
    user_id: str
    user_name: str = "候选人"
    hr_personality_id: str = "hr_smiling_tiger"
    scene_id: str = "scene_001"
    role_id: str = "role_backend"
    status: Literal["ongoing", "settled", "closed"] = "ongoing"
    round_index: int = 1
    max_round: int = 5
    hr_patience: int = 70
    info_exposure: int = 20
    trap_count: int = 0
    current_salary_offer: int = 15000
    equity_ratio: float = 0.0
    law_citation_count: int = 0
    misjudge_count: int = 0
    identified_traps: list[str] = Field(default_factory=list)
    strategy_history: list[str] = Field(default_factory=list)
    conversation_history: list[ConversationMessage] = Field(default_factory=list)
    scene_context: SceneContext


class TextTurnPayload(BaseModel):
    strategy: Optional[StrategyType] = None
    player_text: Optional[str] = None


class TurnResult(BaseModel):
    hr_reply: str
    delta: TurnDelta
    is_trap_hit: bool
    is_game_over: bool
    next_round: int
    inferred_strategy: str = "probe"
    trap_id: str | None = None
    hr_bubble_entrance: Optional[Literal["fade", "slam", "slide"]] = None
    player_bubble_entrance: Optional[Literal["fade", "slam", "slide"]] = None


class FlowDecision(BaseModel):
    next_phase: NextPhase
    reason: str
    should_end: bool = False


class AgentToolCallTrace(BaseModel):
    tool_name: str
    success: bool = True
    transcript: str | None = None
    confidence: float | None = None
    reason: str = ""


class AgentTurnDecision(BaseModel):
    hr_reply: str
    inferred_strategy: str = "probe"
    delta: TurnDelta
    trap_id: str | None = None
    next_phase_hint: NextPhase = "text"
    should_end: bool = False
    reason: str = ""
    tool_trace: list[AgentToolCallTrace] = Field(default_factory=list)
    player_text_used: str = ""


class ScoreBreakdown(BaseModel):
    dq: int
    td: int
    wh: int
    si: int


class OfferPackage(BaseModel):
    equity_ratio: float
    social_security_base: str
    housing_fund_ratio: str
    overtime_policy: str
    working_hours_agreement: str


class SettleStats(BaseModel):
    traps_identified: int
    traps_total: int = 5
    trap_labels: list[str] = Field(default_factory=list)
    law_citation_count: int = 0
    strategy_count: int = 0
    final_patience: int = 0


class SettleResult(BaseModel):
    final_salary: int
    final_score: int
    grade: str
    review_tip: str
    verdict: Literal["hired", "rejected"] = "hired"
    outcome_reason: str = ""
    title: str = ""
    medal: str = ""
    scene_name: str = ""
    summary: str = ""
    risk_notes: list[str] = Field(default_factory=list)
    missed_clauses: list[str] = Field(default_factory=list)
    breakdown: ScoreBreakdown | None = None
    offer: OfferPackage | None = None
    stats: SettleStats | None = None


class PersistResult(BaseModel):
    saved: bool
    user_id: str
    session_id: str
