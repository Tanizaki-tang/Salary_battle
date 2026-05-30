from __future__ import annotations

from app.service.llm_service import llm_state_adjustment
from app.shared_types.game_types import SessionState, TurnResult


def update_state_with_llm(session_state: SessionState, player_text: str, base_turn_result: TurnResult) -> TurnResult:
    """
    输入:
    - session_state: 当前局状态
    - player_text: 玩家输入文本
    - base_turn_result: text/voice 模块输出的基础结果

    输出:
    - TurnResult: 经过 LLM 风格状态修正后的结果

    说明:
    - 仅使用 llm_service 做状态修正。
    - 若 LLM 调用失败，退回 base_turn_result，不做关键词模拟规则。
    """
    result = base_turn_result.model_copy(deep=True)
    try:
        llm = llm_state_adjustment(
            scene_context=session_state.scene_context.model_dump(),
            session_state=session_state.model_dump(),
            player_text=player_text,
            base_turn_result=base_turn_result.model_dump(),
        )
    except Exception:
        return result

    if llm.get("hr_reply"):
        result.hr_reply = llm["hr_reply"]
    result.inferred_strategy = llm.get("inferred_strategy", "probe")
    result.delta.hr_patience = llm.get("delta_hr_patience", result.delta.hr_patience)
    result.delta.info_exposure = llm.get("delta_info_exposure", result.delta.info_exposure)
    result.delta.trap_count = llm.get("delta_trap_count", result.delta.trap_count)
    result.delta.salary_offer = llm.get("delta_salary_offer", 0)
    result.delta.equity_ratio = llm.get("delta_equity_ratio", 0.0)
    result.delta.law_citation_count = llm.get("delta_law_citation_count", 0)
    result.delta.misjudge_count = llm.get("delta_misjudge_count", 0)
    result.trap_id = llm.get("trap_id")
    result.is_trap_hit = bool(result.trap_id) or result.delta.trap_count > 0
    result.is_game_over = bool(llm.get("should_end", False)) or result.is_game_over
    return result
