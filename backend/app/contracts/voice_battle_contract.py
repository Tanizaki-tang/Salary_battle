from __future__ import annotations

from abc import ABC, abstractmethod

from app.shared_types.game_types import SessionState, VoiceTurnPayload, VoiceTurnResult


class VoiceBattleContract(ABC):
    @abstractmethod
    def transcribe_for_agent(self, audio_payload: VoiceTurnPayload) -> dict:
        """
        输入:
        - audio_payload: 语音输入(音频路径/模式)

        输出:
        - {"transcript": str, "confidence": float}
        """
        raise NotImplementedError

    @abstractmethod
    def run_voice_turn(self, session_state: SessionState, audio_payload: VoiceTurnPayload) -> VoiceTurnResult:
        """
        输入:
        - session_state: 当前对局状态
        - audio_payload: 语音输入(音频路径/模式)

        输出:
        - VoiceTurnResult: ASR 结果 + 同构 turn_result
        """
        raise NotImplementedError
