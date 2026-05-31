from __future__ import annotations

from app.shared_types.game_types import SessionState, SettleResult


def settle_session(session_state: SessionState) -> SettleResult:
    """
    输入:
    - session_state: 结算时对局状态

    输出:
    - SettleResult: final_salary/final_score/grade/review_tip

    示例:
    - 输入 hr_patience=70, info_exposure=20, trap_count=1
    - 输出 final_score=81, grade=A
    """
    anchors = session_state.scene_context.salary_anchor
    score_profile = session_state.scene_context.score_profile

    final_salary = max(anchors.legal_floor, min(anchors.ideal_target, session_state.current_salary_offer))

    dq_raw = (final_salary - anchors.legal_floor) / max(1, (anchors.ideal_target - anchors.legal_floor)) * 100
    dq = max(0, min(100, dq_raw))
    td = max(0, min(100, (len(session_state.identified_traps) / 5) * 100 + session_state.law_citation_count * 5 - session_state.misjudge_count * 3))
    wh = max(0, min(100, 100 - session_state.info_exposure))
    si = max(0, min(100, 40 + len(session_state.identified_traps) * 10 + session_state.law_citation_count * 5))

    final_score = int(
        dq * score_profile.dq_weight
        + td * score_profile.td_weight
        + wh * score_profile.wh_weight
        + si * score_profile.si_weight
        + score_profile.bonus_survival
    )
    if len(set(session_state.strategy_history)) >= 3:
        final_score += score_profile.bonus_strategy_diversity
    if session_state.info_exposure > score_profile.high_exposure_threshold:
        final_score -= score_profile.penalty_high_exposure
    final_score = max(0, min(110, final_score))

    grade = "A" if final_score >= score_profile.grade_a else "B" if final_score >= score_profile.grade_b else "C"
    return SettleResult(
        final_salary=final_salary,
        final_score=final_score,
        grade=grade,
        review_tip="你成功控制了信息暴露度，建议继续提升陷阱识别稳定性。",
    )
