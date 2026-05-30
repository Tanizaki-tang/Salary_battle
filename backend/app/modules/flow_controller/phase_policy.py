from __future__ import annotations

from app.shared_types.game_types import FlowDecision, NextPhase, SessionState


def decide_next_phase_with_policy(session_state: SessionState, agent_next_phase_hint: NextPhase | None = None) -> FlowDecision:
    """
    语音触发主规则（Agent-A控制）:
    1) HR满意度 > 80 -> 触发语音
    2) 玩家强势施压/反问逼牌过多，且达到该场景HR的“被激怒阈值” -> 触发语音
    """
    if session_state.status == "settled" or session_state.round_index >= session_state.max_round:
        return FlowDecision(next_phase="end", reason="rule_end_max_round_or_settled", should_end=True)
    if session_state.hr_patience <= 10:
        return FlowDecision(next_phase="end", reason="rule_end_low_patience", should_end=True)

    # Rule-1: HR满意度高时，优先切语音以加速博弈节奏。
    if session_state.hr_patience > 80:
        return FlowDecision(next_phase="voice", reason="rule_voice_high_hr_patience", should_end=False)

    # Rule-2: 强势施压/反问逼牌累计较多，由不同scene的HR性格决定是否被激怒。
    if _is_hr_angered_by_pressure(session_state):
        return FlowDecision(next_phase="voice", reason="rule_voice_hr_angered_by_pressure", should_end=False)

    if agent_next_phase_hint == "end" and session_state.round_index >= 2:
        return FlowDecision(next_phase="end", reason="agent_hint_end", should_end=True)
    if agent_next_phase_hint == "voice":
        return FlowDecision(next_phase="voice", reason="agent_hint_voice", should_end=False)
    if agent_next_phase_hint == "text":
        return FlowDecision(next_phase="text", reason="agent_hint_text", should_end=False)

    return FlowDecision(next_phase="text", reason="default_text_loop", should_end=False)


def _is_hr_angered_by_pressure(session_state: SessionState) -> bool:
    # 仅看最近4轮，避免很早的激进行为永久影响。
    recent = session_state.strategy_history[-4:]
    strong_push_count = sum(1 for s in recent if s == "strong_push")
    counter_pressure_count = sum(1 for s in recent if s == "counter_pressure")
    weighted_pressure = strong_push_count * 1.0 + counter_pressure_count * 1.2

    # scene驱动的“被激怒阈值”：数值越低越容易触发语音对抗。
    scene_threshold = {
        "scene_001": 2.2,  # 务实但可强硬，中等敏感
        "scene_002": 3.0,  # 偏克制，阈值更高
        "scene_003": 1.8,  # 表达直接，更易被逼牌激怒
    }
    threshold = scene_threshold.get(session_state.scene_id, 2.4)
    return weighted_pressure >= threshold
