from __future__ import annotations

from app.modules.flow_controller.persistence_adapter import save_session_result
from app.modules.flow_controller.session_state_machine import advance_game_flow
from app.modules.flow_controller.settle_service import settle_session
from app.modules.text_battle.text_battle_engine import TextBattleEngine
from app.modules.voice_battle.voice_battle_engine import VoiceBattleEngine
from app.shared_types.game_types import (
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
        self.text_engine = TextBattleEngine()
        self.voice_engine = VoiceBattleEngine()

    def run_text_turn(self, session_state: SessionState, text_payload: TextTurnPayload) -> tuple[SessionState, TurnResult]:
        result = self.text_engine.run_text_turn(session_state, text_payload)
        return advance_game_flow(session_state, result), result

    def run_voice_turn(
        self, session_state: SessionState, voice_payload: VoiceTurnPayload
    ) -> tuple[SessionState, VoiceTurnResult]:
        result = self.voice_engine.run_voice_turn(session_state, voice_payload)
        return advance_game_flow(session_state, result.turn_result), result

    async def run_voice_turn_with_tts(
        self, session_state: SessionState, voice_payload: VoiceTurnPayload
    ) -> tuple[SessionState, VoiceTurnResult]:
        result = await self.voice_engine.run_voice_turn_with_tts(session_state, voice_payload)
        return advance_game_flow(session_state, result.turn_result), result

    def settle_and_persist(self, session_state: SessionState) -> tuple[SettleResult, PersistResult]:
        settle_result = settle_session(session_state)
        persist_result = save_session_result(session_state.user_id, settle_result, session_state.session_id)
        return settle_result, persist_result
