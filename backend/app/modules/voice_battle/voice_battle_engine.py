from __future__ import annotations

from app.contracts.voice_battle_contract import VoiceBattleContract
from app.modules.text_battle.text_battle_engine import TextBattleEngine
from app.modules.voice_battle.speech_gateway import transcribe_audio
from app.shared_types.game_types import SessionState, TextTurnPayload, VoiceTurnPayload, VoiceTurnResult


class VoiceBattleEngine(VoiceBattleContract):
    def __init__(self) -> None:
        self._text_engine = TextBattleEngine()

    def transcribe_for_agent(self, audio_payload: VoiceTurnPayload) -> dict:
        try:
            return transcribe_audio(audio_payload)
        except Exception:
            return {"transcript": "", "confidence": 0.0}

    def run_voice_turn(self, session_state: SessionState, audio_payload: VoiceTurnPayload) -> VoiceTurnResult:
        """
        输入:
        - session_state: 当前局状态
        - audio_payload: 音频路径与模式

        输出:
        - VoiceTurnResult:
          asr_text/confidence/turn_result

        示例:
        - 输入 {"audio_path":"demo.wav"} -> 输出 {"asr_text":"...","turn_result":{...}}
        """
        asr = self.transcribe_for_agent(audio_payload)
        turn_result = self._text_engine.run_text_turn(
            session_state,
            TextTurnPayload(player_text=asr["transcript"]),
        )
        return VoiceTurnResult(
            asr_text=asr["transcript"],
            confidence=asr["confidence"],
            turn_result=turn_result,
        )
