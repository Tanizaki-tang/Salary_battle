from __future__ import annotations

import time
from pathlib import Path

from app.modules.voice_battle.speech_gateway import AsrPipelineError, transcribe_file
from app.shared_types.game_types import VoiceTurnPayload


class VoiceBattleEngine:
    def transcribe_for_agent(self, audio_payload: VoiceTurnPayload, mime_type: str | None = None) -> dict:
        resolved_mime = mime_type or audio_payload.mime_type
        return transcribe_file(audio_payload.audio_path, mime_type=resolved_mime)
