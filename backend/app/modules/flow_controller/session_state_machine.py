from __future__ import annotations

from app.modules.flow_controller.salary_concession import apply_salary_offer
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
    next_state.current_salary_offer = apply_salary_offer(next_state, turn_result.delta.salary_offer)
    next_state.equity_ratio = max(0.0, min(0.5, next_state.equity_ratio + turn_result.delta.equity_ratio))
    next_state.law_citation_count = max(0, next_state.law_citation_count + turn_result.delta.law_citation_count)
    next_state.misjudge_count = max(0, next_state.misjudge_count + turn_result.delta.misjudge_count)
    if turn_result.inferred_strategy:
        next_state.strategy_history.append(turn_result.inferred_strategy)
    if turn_result.trap_id and turn_result.trap_id not in next_state.identified_traps:
        next_state.identified_traps.append(turn_result.trap_id)
    next_state.round_index = turn_result.next_round
    if turn_result.is_game_over or next_state.hr_patience <= 10:
        next_state.status = "settled"
    return next_state
