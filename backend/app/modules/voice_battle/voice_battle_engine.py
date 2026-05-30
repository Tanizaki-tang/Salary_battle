from __future__ import annotations

from app.contracts.voice_battle_contract import VoiceBattleContract
from app.modules.text_battle.text_battle_engine import TextBattleEngine
from app.modules.voice_battle.speech_gateway import transcribe_audio
from app.modules.voice_battle.tts_gateway import SpeechSynthesisError, synthesize_speech
from app.shared_types.game_types import SessionState, TextTurnPayload, VoiceTurnPayload, VoiceTurnResult


class VoiceBattleEngine(VoiceBattleContract):
    def __init__(self) -> None:
        self._text_engine = TextBattleEngine()

    def transcribe_only(self, audio_payload: VoiceTurnPayload) -> dict:
        return transcribe_audio(audio_payload)

    def run_voice_turn(self, session_state: SessionState, audio_payload: VoiceTurnPayload) -> VoiceTurnResult:
        asr = self.transcribe_only(audio_payload)
        turn_result = self._text_engine.run_text_turn(
            session_state,
            TextTurnPayload(player_text=asr["transcript"]),
        )
        return VoiceTurnResult(
            asr_text=asr["transcript"],
            confidence=asr["confidence"],
            turn_result=turn_result,
        )

    async def run_voice_turn_with_tts(
        self, session_state: SessionState, audio_payload: VoiceTurnPayload
    ) -> VoiceTurnResult:
        result = self.run_voice_turn(session_state, audio_payload)
        try:
            tts = await synthesize_speech(result.turn_result.hr_reply)
            result.hr_audio_path = tts["audio_path"]
            result.tts_voice = tts["voice"]
        except SpeechSynthesisError as exc:
            result.tts_error = str(exc)
        return result
