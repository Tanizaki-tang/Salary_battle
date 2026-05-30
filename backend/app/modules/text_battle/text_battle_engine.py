from __future__ import annotations

from app.contracts.text_battle_contract import TextBattleContract
from app.modules.text_battle.strategy_parser import normalize_strategy
from app.shared_types.game_types import SessionState, TextTurnPayload, TurnDelta, TurnResult


class TextBattleEngine(TextBattleContract):
    def run_text_turn(self, session_state: SessionState, text_payload: TextTurnPayload) -> TurnResult:
        """
        输入:
        - session_state: 当前局状态
        - text_payload: strategy 或 player_text

        输出:
        - TurnResult:
          hr_reply/delta/is_trap_hit/is_game_over/next_round

        示例输入:
        - session_state.round_index=1, text_payload={"strategy":"probe"}
        示例输出:
        - {"hr_reply":"你可以先说说你的预期范围。","delta":{"hr_patience":-2,...}}
        """
        strategy = normalize_strategy(text_payload)
        scene_context = session_state.scene_context
        strategy_delta = scene_context.strategy_delta_map[strategy]
        reply = scene_context.tone_map[strategy]
        is_over = session_state.round_index >= session_state.max_round
        return TurnResult(
            hr_reply=reply,
            delta=TurnDelta(
                hr_patience=strategy_delta.hr_patience,
                info_exposure=strategy_delta.info_exposure,
                trap_count=strategy_delta.trap_count,
            ),
            is_trap_hit=strategy_delta.trap_count > 0,
            is_game_over=is_over,
            next_round=min(session_state.round_index + 1, session_state.max_round),
        )
