from __future__ import annotations

from app.modules.agent.hr_negotiation_agent import HrNegotiationAgent
from app.modules.agent.tools.voice_battle_tool import VoiceBattleTool
from app.modules.flow_controller.phase_router import decide_next_phase
from app.modules.flow_controller.persistence_adapter import save_session_result
from app.modules.flow_controller.session_state_machine import advance_game_flow
from app.modules.flow_controller.settle_service import settle_session
from app.modules.voice_battle.voice_battle_engine import VoiceBattleEngine
from app.shared_types.game_types import (
    AgentTurnDecision,
    FlowDecision,
    PersistResult,
    SessionState,
    SettleResult,
    TextTurnPayload,
    TurnResult,
    VoiceTurnPayload,
    VoiceTurnResult,
)


class GameFlowOrchestrator:
    def __init__(self) -> None:
        self.voice_engine = VoiceBattleEngine()
        self.voice_tool = VoiceBattleTool(self.voice_engine)
        self.hr_agent = HrNegotiationAgent(self.voice_tool)

    def run_text_turn(
        self, session_state: SessionState, text_payload: TextTurnPayload
    ) -> tuple[SessionState, TurnResult, FlowDecision]:
        player_text = text_payload.player_text or text_payload.strategy or ""
        decision = self.hr_agent.decide_text_turn(session_state, player_text)
        turn_result = self._decision_to_turn_result(session_state, decision)
        next_state = advance_game_flow(session_state, turn_result)
        flow = decide_next_phase(next_state, decision.next_phase_hint)
        return next_state, turn_result, flow

    def run_voice_turn(
        self, session_state: SessionState, voice_payload: VoiceTurnPayload
    ) -> tuple[SessionState, VoiceTurnResult, FlowDecision]:
        decision = self.hr_agent.decide_voice_turn(session_state, voice_payload)
        turn_result = self._decision_to_turn_result(session_state, decision)
        next_state = advance_game_flow(session_state, turn_result)
        flow = decide_next_phase(next_state, decision.next_phase_hint)
        first_trace = decision.tool_trace[0] if decision.tool_trace else None
        voice_result = VoiceTurnResult(
            asr_text=(first_trace.transcript if first_trace else "") or decision.player_text_used,
            confidence=(first_trace.confidence if first_trace else 0.0) or 0.0,
            turn_result=turn_result,
        )
        return next_state, voice_result, flow

    def decide_next_phase(self, session_state: SessionState, agent_hint: str | None = None) -> FlowDecision:
        return decide_next_phase(session_state, agent_hint)

    def settle_and_persist(self, session_state: SessionState) -> tuple[SettleResult, PersistResult]:
        settle_result = settle_session(session_state)
        persist_result = save_session_result(session_state.user_id, settle_result, session_state.session_id)
        return settle_result, persist_result

    @staticmethod
    def _decision_to_turn_result(session_state: SessionState, decision: AgentTurnDecision) -> TurnResult:
        next_round = min(session_state.round_index + 1, session_state.max_round)
        return TurnResult(
            hr_reply=decision.hr_reply,
            delta=decision.delta,
            is_trap_hit=bool(decision.trap_id) or decision.delta.trap_count > 0,
            is_game_over=decision.should_end or next_round >= session_state.max_round,
            next_round=next_round,
            inferred_strategy=decision.inferred_strategy,
            trap_id=decision.trap_id,
        )
