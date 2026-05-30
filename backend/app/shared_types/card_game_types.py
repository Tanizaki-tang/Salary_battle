from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

CardStrategyId = Literal[
    "strong_push",
    "probe",
    "concede",
    "counter_pressure",
    "expose_rhetoric",
    "off_topic",
]

CardGameStatus = Literal["ongoing", "collapsed", "accepted", "forced_settle", "settled"]
CardGameOutcome = Literal["collapsed", "high_deal", "deal", "low_deal", "forced_deal"]


class CardGameStats(BaseModel):
    satisfaction: float = 6.0
    salary_k: float = 15.0
    work_hours: float = 2.0
    security: float = 1.0


class CardGameState(BaseModel):
    session_id: str
    user_id: str
    user_name: str = "候选人"
    hr_personality_id: str = "hr_smiling_tiger"
    status: CardGameStatus = "ongoing"
    round_index: int = 1
    max_round: int = 8
    stats: CardGameStats = Field(default_factory=CardGameStats)
    current_question: str = ""
    available_strategies: list[CardStrategyId] = Field(default_factory=list)
    option_replies: dict[str, str] = Field(default_factory=dict)
    recommended_strategy: Optional[CardStrategyId] = None
    last_hr_reply: str = ""
    last_player_text: str = ""
    last_strategy: Optional[CardStrategyId] = None
    strategy_history: list[CardStrategyId] = Field(default_factory=list)
    outcome: Optional[CardGameOutcome] = None


class CardTurnPayload(BaseModel):
    strategy: CardStrategyId
    player_text: Optional[str] = None


class CardDeltaView(BaseModel):
    satisfaction: int
    salary_k: float
    work_hours: int
    security: int


class CardTurnResult(BaseModel):
    hr_reply: str
    player_text_used: str = ""
    next_question: str
    available_strategies: list[CardStrategyId] = Field(default_factory=list)
    delta: CardDeltaView
    stats: CardGameStats
    round_index: int
    is_game_over: bool
    recommended_strategy: Optional[CardStrategyId] = None
    outcome: Optional[CardGameOutcome] = None
    outcome_reason: str = ""
    option_replies: dict[str, str] = Field(default_factory=dict)


class CardGameScoreBreakdown(BaseModel):
    salary: int
    work_hours: int
    security: int
    satisfaction: int


class CardGameSettleResult(BaseModel):
    final_score: int
    grade: str
    medal: str
    title: str
    outcome: CardGameOutcome
    review_tip: str
    conditions_met: int
    breakdown: CardGameScoreBreakdown
    stats: CardGameStats
    strategy_count: int
    bonus_diversity: int = 0
    penalty_low_satisfaction: int = 0
