from __future__ import annotations

from app.shared_types.game_types import SessionState, TurnResult


def advance_game_flow(session_state: SessionState, turn_result: TurnResult) -> SessionState:
    """
    输入:
    - session_state: 旧状态
    - turn_result: 当前回合输出

    输出:
    - SessionState: 更新后的状态

    示例:
    - 输入 round_index=1 + delta(-2,-6,+0)
    - 输出 round_index=2, hr_patience=68, info_exposure=14
    """
    next_state = session_state.model_copy(deep=True)
    next_state.hr_patience = max(0, min(100, next_state.hr_patience + turn_result.delta.hr_patience))
    next_state.info_exposure = max(0, min(100, next_state.info_exposure + turn_result.delta.info_exposure))
    next_state.trap_count = max(0, next_state.trap_count + turn_result.delta.trap_count)
    next_state.round_index = turn_result.next_round
    if turn_result.is_game_over or next_state.hr_patience <= 0:
        next_state.status = "settled"
    return next_state
