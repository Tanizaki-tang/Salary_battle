from __future__ import annotations

import logging
import os

from app.shared_types.game_types import FlowDecision, NextPhase, SessionState

logger = logging.getLogger(__name__)


def decide_next_phase(session_state: SessionState, agent_next_phase_hint: NextPhase | None = None) -> FlowDecision:
    """
    语音触发主规则:
    1) HR满意度 > 80 -> 触发语音
    2) 玩家强势施压/反问逼牌过多，且达到该场景HR的“被激怒阈值” -> 触发语音
    """
    effective_max_round = resolve_effective_max_round(session_state.max_round)
    if session_state.status == "settled" or session_state.round_index >= effective_max_round:
        return FlowDecision(next_phase="end", reason="rule_end_max_round_or_settled", should_end=True)
    if session_state.hr_patience <= 10:
        return FlowDecision(next_phase="end", reason="rule_end_low_patience", should_end=True)

    if session_state.hr_patience > 80:
        return FlowDecision(next_phase="voice", reason="rule_voice_high_hr_patience", should_end=False)

    if _is_hr_angered_by_pressure(session_state):
        return FlowDecision(next_phase="voice", reason="rule_voice_hr_angered_by_pressure", should_end=False)

    if agent_next_phase_hint == "end" and session_state.round_index >= 2:
        return FlowDecision(next_phase="end", reason="agent_hint_end", should_end=True)
    if agent_next_phase_hint == "voice":
        return FlowDecision(next_phase="voice", reason="agent_hint_voice", should_end=False)
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


def _is_hr_angered_by_pressure(session_state: SessionState) -> bool:
    recent = session_state.strategy_history[-4:]
    strong_push_count = sum(1 for s in recent if s == "strong_push")
    counter_pressure_count = sum(1 for s in recent if s == "counter_pressure")
    weighted_pressure = strong_push_count * 1.0 + counter_pressure_count * 1.2

    scene_threshold = {
        "scene_001": 2.2,
        "scene_002": 3.0,
        "scene_003": 1.8,
    }
    threshold = scene_threshold.get(session_state.scene_id, 2.4)
    return weighted_pressure >= threshold
