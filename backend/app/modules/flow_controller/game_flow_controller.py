from __future__ import annotations

from app.modules.flow_controller.llm_state_updater import update_state_with_llm
from app.modules.flow_controller.phase_router import decide_next_phase
from app.modules.flow_controller.session_state_machine import advance_game_flow
from app.modules.text_battle.text_battle_engine import TextBattleEngine
from app.modules.voice_battle.voice_battle_engine import VoiceBattleEngine
from app.shared_types.game_types import (
    FlowDecision,
    SessionState,
    TextTurnPayload,
    TurnResult,
    VoiceTurnPayload,
    VoiceTurnResult,
)


class GameFlowController:
    """
    游戏流程控制器（核心链路）

    流程:
    1) 前端选角色/场景后创建 SessionState（HR 首条消息由 scene_context.opening_line 给出）
    2) 交替回合:
       - 文本回合: text_battle_contract -> LLM状态更新 -> 状态推进 -> 决策下一阶段
       - 语音回合: voice_battle_contract -> LLM状态更新 -> 状态推进 -> 决策下一阶段
    3) next_phase == end 时进入结算流程
    """

    def __init__(self) -> None:
        self.text_engine = TextBattleEngine()
        self.voice_engine = VoiceBattleEngine()

    def process_text_round(self, session_state: SessionState, payload: TextTurnPayload) -> tuple[SessionState, TurnResult, FlowDecision]:
        """
        输入:
        - session_state: 当前会话状态
        - payload: 文本回合输入

        输出:
        - (next_state, turn_result, flow_decision)
        """
        base_result = self.text_engine.run_text_turn(session_state, payload)
        player_text = payload.player_text or payload.strategy or ""
        llm_result = update_state_with_llm(session_state, player_text, base_result)
        next_state = advance_game_flow(session_state, llm_result)
        decision = decide_next_phase(next_state)
        return next_state, llm_result, decision

    def process_voice_round(
        self, session_state: SessionState, payload: VoiceTurnPayload
    ) -> tuple[SessionState, VoiceTurnResult, FlowDecision]:
        """
        输入:
        - session_state: 当前会话状态
        - payload: 语音回合输入

        输出:
        - (next_state, voice_turn_result, flow_decision)
        """
        voice_result = self.voice_engine.run_voice_turn(session_state, payload)
        llm_result = update_state_with_llm(session_state, voice_result.asr_text, voice_result.turn_result)
        voice_result.turn_result = llm_result
        next_state = advance_game_flow(session_state, voice_result.turn_result)
        decision = decide_next_phase(next_state)
        return next_state, voice_result, decision
