from __future__ import annotations

import base64

from app.modules.voice_battle.speech_gateway import AsrPipelineError, transcribe_bytes


class RealtimeVoiceService:
    def __init__(self) -> None:
        self._chunks: list[bytes] = []
        self._received_bytes: int = 0

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    @property
    def received_bytes(self) -> int:
        return self._received_bytes

    def append_chunk_base64(self, chunk_base64: str) -> None:
        import base64

        data = base64.b64decode(chunk_base64)
        if not data:
            return
        self._chunks.append(data)
        self._received_bytes += len(data)

    def reset(self) -> None:
        self._chunks.clear()
        self._received_bytes = 0

    def transcribe_current_audio(self, mime_type: str = "audio/wav") -> dict:
        if not self._chunks:
            return {"transcript": "", "confidence": 0.0}
        return transcribe_bytes(b"".join(self._chunks), mime_type=mime_type)
