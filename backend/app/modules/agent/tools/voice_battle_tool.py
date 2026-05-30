from __future__ import annotations

from app.modules.voice_battle.voice_battle_engine import VoiceBattleEngine
from app.shared_types.game_types import AgentToolCallTrace, VoiceTurnPayload


class VoiceBattleTool:
    """Expose voice_battle as an agent-callable tool."""

    def __init__(self, voice_engine: VoiceBattleEngine) -> None:
        self._voice_engine = voice_engine

    def transcribe_for_agent(self, payload: VoiceTurnPayload) -> tuple[str, float, AgentToolCallTrace]:
        asr = self._voice_engine.transcribe_for_agent(payload, mime_type=payload.mime_type)
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
