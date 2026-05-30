from __future__ import annotations

from dataclasses import dataclass

from app.shared_types.game_types import SessionState

# willingness: 让步意愿越高，LLM 请求的涨幅越容易落地
# marginal_difficulty: 每已在初始报价之上涨 1K，后续涨幅额外衰减（越大越难继续涨）
_CONCESSION_BY_PERSONALITY: dict[str, tuple[float, float]] = {
    "hr_newbie": (1.0, 0.06),
    "hr_honest": (0.88, 0.10),
    "hr_smiling_tiger": (0.68, 0.16),
    "hr_robot": (0.38, 0.24),
    "hr_aggressive": (0.22, 0.32),
}

_DEFAULT_CONCESSION = (0.65, 0.15)


@dataclass(frozen=True, slots=True)
class ConcessionProfile:
    personality_id: str
    willingness: float
    marginal_difficulty: float


def get_concession_profile(personality_id: str | None) -> ConcessionProfile:
    pid = (personality_id or "").strip() or "hr_smiling_tiger"
    willingness, marginal = _CONCESSION_BY_PERSONALITY.get(pid, _DEFAULT_CONCESSION)
    return ConcessionProfile(
        personality_id=pid,
        willingness=willingness,
        marginal_difficulty=marginal,
    )


def k_above_initial_offer(session_state: SessionState) -> int:
    anchor = session_state.scene_context.salary_anchor
    return max(0, (session_state.current_salary_offer - anchor.hr_initial_offer) // 1000)


def marginal_raise_factor(session_state: SessionState) -> float:
    """当前薪资水平下，下一笔涨幅的边际难度系数 (0~1]。"""
    profile = get_concession_profile(session_state.hr_personality_id)
    steps = k_above_initial_offer(session_state)
    return profile.willingness / (1.0 + steps * profile.marginal_difficulty)


def compute_effective_salary_delta(session_state: SessionState, requested_delta: int) -> int:
    """将 LLM/策略请求的涨幅，按人格让步曲线折算为实际落地涨幅。"""
    if requested_delta <= 0:
        return 0
    factor = marginal_raise_factor(session_state)
    return max(0, int(requested_delta * factor))


def apply_salary_offer(session_state: SessionState, requested_delta: int) -> int:
    """返回应用人格让步曲线后的新报价（仅保留下限，无薪资上限）。"""
    anchor = session_state.scene_context.salary_anchor
    effective = compute_effective_salary_delta(session_state, requested_delta)
    return max(anchor.legal_floor, session_state.current_salary_offer + effective)
