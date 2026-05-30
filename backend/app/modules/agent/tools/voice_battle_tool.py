from __future__ import annotations

from app.contracts.voice_battle_contract import VoiceBattleContract
from app.shared_types.game_types import AgentToolCallTrace, VoiceTurnPayload


class VoiceBattleTool:
    """Expose voice_battle as an agent-callable tool."""

    def __init__(self, voice_contract: VoiceBattleContract) -> None:
        self._voice_contract = voice_contract

    def transcribe_for_agent(self, payload: VoiceTurnPayload) -> tuple[str, float, AgentToolCallTrace]:
        asr = self._voice_contract.transcribe_for_agent(payload)
        transcript = str(asr.get("transcript", "")).strip()
        confidence = float(asr.get("confidence", 0.0))
        trace = AgentToolCallTrace(
            tool_name="voice_battle",
            success=bool(transcript),
            transcript=transcript or None,
            confidence=confidence,
            reason="voice_tool_called",
        )
        return transcript, confidence, trace
