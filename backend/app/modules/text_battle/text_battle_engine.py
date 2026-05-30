from __future__ import annotations

from app.contracts.text_battle_contract import TextBattleContract
from app.modules.text_battle.strategy_parser import normalize_strategy
from app.shared_types.game_types import SessionState, TextTurnPayload, TurnDelta, TurnResult


class TextBattleEngine(TextBattleContract):
    STRATEGY_DELTA = {
        "strong_push": (-8, -2, 0, "这个预算已经比较紧了。"),
        "probe": (-2, -6, 0, "你可以先说说你的预期范围。"),
        "concede": (6, 8, 0, "那我们按标准流程推进。"),
        "counter_pressure": (-5, -5, 1, "这个点我们再沟通下。"),
    }

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
        delta_patience, delta_exposure, delta_trap, reply = self.STRATEGY_DELTA[strategy]
        is_over = session_state.round_index >= session_state.max_round
        return TurnResult(
            hr_reply=reply,
            delta=TurnDelta(
                hr_patience=delta_patience,
                info_exposure=delta_exposure,
                trap_count=delta_trap,
            ),
            is_trap_hit=delta_trap > 0,
            is_game_over=is_over,
            next_round=min(session_state.round_index + 1, session_state.max_round),
        )
