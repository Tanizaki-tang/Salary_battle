from __future__ import annotations

from abc import ABC, abstractmethod

from app.shared_types.game_types import (
    AgentTurnDecision,
    FlowDecision,
    NextPhase,
    PersistResult,
    SceneContext,
    SessionState,
    SettleResult,
    TurnResult,
    VoiceTurnPayload,
)


class FlowContract(ABC):
    @abstractmethod
    def resolve_scene_context(self, scene_id: str | None = None, role_id: str | None = None) -> SceneContext:
        """
        输入:
        - scene_id: 前端传入的场景ID(可选)
        - role_id: 前端传入的角色ID(可选)

        输出:
        - SceneContext: 后端解析后的场景上下文
        """
        raise NotImplementedError

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
    def generate_agent_turn_decision(
        self,
        session_state: SessionState,
        player_text: str,
        input_mode: str = "text",
        voice_payload: VoiceTurnPayload | None = None,
    ) -> AgentTurnDecision:
        """
        输入:
        - session_state: 当前状态
        - player_text: 玩家输入文本
        - input_mode: text/voice
        - voice_payload: 语音回合的音频上下文(可选)

        输出:
        - AgentTurnDecision: Agent结构化决策
        """
        raise NotImplementedError

    @abstractmethod
    def decide_next_phase(self, session_state: SessionState, agent_next_phase_hint: NextPhase | None = None) -> FlowDecision:
        """
        输入:
        - session_state: 更新后的状态

        输出:
        - FlowDecision: 下一阶段(text/voice/end)和原因
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
