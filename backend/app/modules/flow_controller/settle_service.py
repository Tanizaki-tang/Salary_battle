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
    final_score = int(
        session_state.hr_patience * 0.5
        + (100 - session_state.info_exposure) * 0.3
        + session_state.trap_count * 20 * 0.2
    )
    grade = "A" if final_score >= 80 else "B" if final_score >= 65 else "C"
    final_salary = 11000 + session_state.hr_patience * 20 - session_state.info_exposure * 10 + session_state.trap_count * 200
    return SettleResult(
        final_salary=max(8000, final_salary),
        final_score=final_score,
        grade=grade,
        review_tip="你成功控制了信息暴露度，建议继续提升陷阱识别稳定性。",
    )
