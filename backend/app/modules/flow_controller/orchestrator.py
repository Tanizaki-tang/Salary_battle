from __future__ import annotations

import logging
import time

from app.modules.agent.hr_negotiation_agent import HrNegotiationAgent
from app.modules.fantasy_events.fantasy_events import pick_fantasy_event
from app.modules.flow_controller.persistence_adapter import save_session_result
from app.modules.flow_controller.phase_policy import decide_next_phase, resolve_effective_max_round
from app.modules.flow_controller.session_state_machine import advance_game_flow
from app.modules.flow_controller.settle_service import settle_session
from app.service.llm_service import llm_latency_enabled
from app.shared_types.game_types import (
    AgentTurnDecision,
    ConversationMessage,
    FlowDecision,
    PersistResult,
    SessionState,
    SettleResult,
    TextTurnPayload,
    TurnResult,
)

logger = logging.getLogger(__name__)


class GameFlowOrchestrator:
    def __init__(self) -> None:
        self.hr_agent = HrNegotiationAgent()

    def run_text_turn(
        self, session_state: SessionState, text_payload: TextTurnPayload
    ) -> tuple[SessionState, TurnResult, FlowDecision]:
        started = time.perf_counter()
        player_text = text_payload.player_text or text_payload.strategy or ""
        event = pick_fantasy_event(session_state.session_id, round_index=session_state.round_index, salt=player_text[:32])
        if event is not None:
            session_state.fantasy_event_id = event.event_id
            session_state.fantasy_event_title = event.title
            session_state.fantasy_event_announce = event.announce
            session_state.conversation_history.append(
                ConversationMessage(role="system", content=f"【事件】{event.title}：{event.announce}", round_index=session_state.round_index)
            )
        t0 = time.perf_counter()
        decision = self.hr_agent.decide_text_turn(session_state, player_text)
        t1 = time.perf_counter()
        turn_result = self._decision_to_turn_result(session_state, decision)
        if event is not None:
            turn_result.fantasy_event_id = event.event_id
            turn_result.fantasy_event_title = event.title
            turn_result.fantasy_event_announce = event.announce
        next_state = advance_game_flow(session_state, turn_result)
        t2 = time.perf_counter()
        self._append_round_history(next_state, decision.player_text_used, turn_result.hr_reply, turn_result.next_round)
        flow = decide_next_phase(next_state, decision.next_phase_hint)
        t3 = time.perf_counter()
        logger.info(
            "HR_REPLY_TEXT session_id=%s round=%s next_round=%s next_phase=%s reason=%s reply_preview=%s",
            session_state.session_id,
            session_state.round_index,
            turn_result.next_round,
            flow.next_phase,
            flow.reason,
            (turn_result.hr_reply or "")[:48],
        )
        if llm_latency_enabled():
            logger.info(
                "LATENCY_TEXT_TURN session_id=%s round=%s total_ms=%.1f agent_ms=%.1f advance_ms=%.1f phase_ms=%.1f",
                session_state.session_id,
                session_state.round_index,
                (t3 - started) * 1000,
                (t1 - t0) * 1000,
                (t2 - t1) * 1000,
                (t3 - t2) * 1000,
            )
        return next_state, turn_result, flow

    def settle_and_persist(self, session_state: SessionState) -> tuple[SettleResult, PersistResult]:
        settle_result = settle_session(session_state)
        persist_result = save_session_result(session_state.user_id, settle_result, session_state.session_id)
        return settle_result, persist_result

    @staticmethod
    def _decision_to_turn_result(session_state: SessionState, decision: AgentTurnDecision) -> TurnResult:
        effective_max_round = resolve_effective_max_round(session_state.max_round)
        next_round = min(session_state.round_index + 1, effective_max_round)
        return TurnResult(
            hr_reply=decision.hr_reply,
            delta=decision.delta,
            is_trap_hit=bool(decision.trap_id) or decision.delta.trap_count > 0,
            is_game_over=decision.should_end or next_round >= effective_max_round,
            next_round=next_round,
            inferred_strategy=decision.inferred_strategy,
            trap_id=decision.trap_id,
        )

    @staticmethod
    def _append_round_history(session_state: SessionState, player_text: str, hr_reply: str, round_index: int) -> None:
        if player_text.strip():
            session_state.conversation_history.append(
                ConversationMessage(role="player", content=player_text.strip(), round_index=round_index)
            )
        if hr_reply.strip():
            session_state.conversation_history.append(
                ConversationMessage(role="hr", content=hr_reply.strip(), round_index=round_index)
            )
