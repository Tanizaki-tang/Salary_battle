from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Any

from app.modules.agent.hr_negotiation_agent import HrNegotiationAgent
from app.prompt.dialogue_style import clamp_hr_reply
from app.modules.flow_controller.persistence_adapter import save_session_result
from app.modules.flow_controller.phase_policy import decide_next_phase, resolve_effective_max_round
from app.modules.flow_controller.session_state_machine import advance_game_flow
from app.modules.flow_controller.settle_service import settle_session
from app.service.llm_service import llm_latency_enabled
from app.service.voice_game_point_service import apply_game_point_effects, infer_game_point_hint, sync_game_point_state
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
        t0 = time.perf_counter()
        decision = self.hr_agent.decide_text_turn(session_state, player_text)
        decision.delta = apply_game_point_effects(session_state, player_text=player_text, delta=decision.delta)
        decision.game_point_hint = infer_game_point_hint(
            session_state,
            hr_reply=decision.hr_reply,
            player_text=player_text,
            delta=decision.delta,
        )
        t1 = time.perf_counter()
        turn_result = self._decision_to_turn_result(session_state, decision)
        next_state = advance_game_flow(session_state, turn_result)
        sync_game_point_state(next_state, turn_result.game_point_hint)
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

    def iter_text_turn(
        self,
        session_state: SessionState,
        text_payload: TextTurnPayload,
    ) -> Iterator[dict[str, Any]]:
        """SSE 事件：token → done（含 result/session/flow）。"""
        started = time.perf_counter()
        player_text = (text_payload.player_text or text_payload.strategy or "").strip()
        if not player_text:
            player_text = "我希望了解这份 offer 的组成和边界。"

        reply_parts: list[str] = []
        for chunk in self.hr_agent.iter_hr_reply_chunks(
            session_state=session_state,
            player_text=player_text,
        ):
            reply_parts.append(chunk)
            yield {"event": "token", "text": chunk}

        hr_reply_raw = clamp_hr_reply("".join(reply_parts))
        if hr_reply_raw.strip():
            decision = self.hr_agent.decide_state_from_reply(
                session_state=session_state,
                player_text=player_text,
                hr_reply_raw=hr_reply_raw,
                traces=[],
            )
        else:
            decision = self.hr_agent._safe_default_decision(
                session_state=session_state,
                player_text=player_text,
                traces=[],
            )

        decision.delta = apply_game_point_effects(session_state, player_text=player_text, delta=decision.delta)
        decision.game_point_hint = infer_game_point_hint(
            session_state,
            hr_reply=decision.hr_reply,
            player_text=player_text,
            delta=decision.delta,
        )
        turn_result = self._decision_to_turn_result(session_state, decision)
        next_state = advance_game_flow(session_state, turn_result)
        sync_game_point_state(next_state, turn_result.game_point_hint)
        self._append_round_history(next_state, decision.player_text_used, turn_result.hr_reply, turn_result.next_round)
        flow = decide_next_phase(next_state, decision.next_phase_hint)

        logger.info(
            "HR_REPLY_STREAM session_id=%s round=%s next_round=%s next_phase=%s reply_preview=%s",
            session_state.session_id,
            session_state.round_index,
            turn_result.next_round,
            flow.next_phase,
            (turn_result.hr_reply or "")[:48],
        )
        if llm_latency_enabled():
            logger.info(
                "LATENCY_TEXT_TURN_STREAM session_id=%s round=%s total_ms=%.1f",
                session_state.session_id,
                session_state.round_index,
                (time.perf_counter() - started) * 1000,
            )

        yield {
            "event": "done",
            "result": turn_result.model_dump(),
            "session": next_state.model_dump(),
            "flow": flow.model_dump(),
        }

    def settle_and_persist(self, session_state: SessionState) -> tuple[SettleResult, PersistResult]:
        settle_result = settle_session(session_state)
        persist_result = save_session_result(session_state, settle_result)
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
            game_point_hint=decision.game_point_hint,
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
