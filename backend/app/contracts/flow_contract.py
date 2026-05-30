from __future__ import annotations

from abc import ABC, abstractmethod

from app.shared_types.game_types import PersistResult, SessionState, SettleResult, TurnResult


class FlowContract(ABC):
    @abstractmethod
    def advance_game_flow(self, session_state: SessionState, turn_result: TurnResult) -> SessionState:
        """
        输入:
        - session_state: 旧状态
        - turn_result: 本回合结果

        输出:
        - SessionState: 推进后的新状态
        """
        raise NotImplementedError

    @abstractmethod
    def settle_session(self, session_state: SessionState) -> SettleResult:
        """
        输入:
        - session_state: 结算时状态

        输出:
        - SettleResult: 最终报价/得分/评级/复盘
        """
        raise NotImplementedError

    @abstractmethod
    def save_session_result(self, user_id: str, session_result: SettleResult, session_id: str) -> PersistResult:
        """
        输入:
        - user_id: 用户ID
        - session_result: 结算结果
        - session_id: 对局ID

        输出:
        - PersistResult: 持久化结果
        """
        raise NotImplementedError
