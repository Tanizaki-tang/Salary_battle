from __future__ import annotations

from abc import ABC, abstractmethod

from app.shared_types.game_types import SessionState, TextTurnPayload, TurnResult


class TextBattleContract(ABC):
    @abstractmethod
    def run_text_turn(self, session_state: SessionState, text_payload: TextTurnPayload) -> TurnResult:
        """
        输入:
        - session_state: 当前对局状态
        - text_payload: 文本输入(策略或自由文本)

        输出:
        - TurnResult: 回合输出(回复、指标变化、是否结束)
        """
        raise NotImplementedError
