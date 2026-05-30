from __future__ import annotations

import logging
import os

from app.shared_types.game_types import FlowDecision, NextPhase, SessionState

logger = logging.getLogger(__name__)


def decide_next_phase(session_state: SessionState, agent_next_phase_hint: NextPhase | None = None) -> FlowDecision:
    """文字谈判阶段流转：仅 text / end。"""
    effective_max_round = resolve_effective_max_round(session_state.max_round)
    if session_state.status == "settled" or session_state.round_index >= effective_max_round:
        return FlowDecision(next_phase="end", reason="rule_end_max_round_or_settled", should_end=True)
    if session_state.hr_patience <= 10:
        return FlowDecision(next_phase="end", reason="rule_end_low_patience", should_end=True)

    if agent_next_phase_hint == "end" and session_state.round_index >= 2:
        return FlowDecision(next_phase="end", reason="agent_hint_end", should_end=True)
    if agent_next_phase_hint == "text":
        return FlowDecision(next_phase="text", reason="agent_hint_text", should_end=False)

    return FlowDecision(next_phase="text", reason="default_text_loop", should_end=False)


def resolve_effective_max_round(scene_max_round: int) -> int:
    cap_text = os.getenv("GAME_IMPLICIT_MAX_ROUND", "").strip()
    if not cap_text:
        return max(1, int(scene_max_round))
    try:
        cap = int(cap_text)
    except ValueError:
        logger.warning("Invalid GAME_IMPLICIT_MAX_ROUND=%s, fallback to scene max_round=%s", cap_text, scene_max_round)
        return max(1, int(scene_max_round))
    if cap <= 0:
        logger.warning("Non-positive GAME_IMPLICIT_MAX_ROUND=%s, fallback to scene max_round=%s", cap, scene_max_round)
        return max(1, int(scene_max_round))
    return min(max(1, int(scene_max_round)), cap)
