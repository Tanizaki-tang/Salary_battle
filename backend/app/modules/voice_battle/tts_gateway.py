from __future__ import annotations

import os
import tempfile
from pathlib import Path


DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


class SpeechSynthesisError(RuntimeError):
    pass


def tts_output_dir() -> Path:
    configured = os.getenv("EDGE_TTS_OUTPUT_DIR")
    path = Path(configured) if configured else Path(tempfile.gettempdir()) / "salary_battle_tts"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def synthesize_speech(text: str) -> dict:
    """
    Convert HR reply text into an mp3 file using edge-tts.

    Environment variables:
    - EDGE_TTS_VOICE: voice name, defaults to zh-CN-XiaoxiaoNeural
    - EDGE_TTS_RATE: speaking rate, defaults to +0%
    - EDGE_TTS_VOLUME: volume, defaults to +0%
    - EDGE_TTS_PITCH: pitch, defaults to +0Hz
    - EDGE_TTS_OUTPUT_DIR: mp3 output directory, defaults to system temp
    """
    if not text.strip():
        raise SpeechSynthesisError("TTS text is empty")

    try:
        import edge_tts
    except ImportError as exc:
        raise SpeechSynthesisError("edge-tts is not installed in this Python environment") from exc

    voice = os.getenv("EDGE_TTS_VOICE", DEFAULT_VOICE)
    rate = os.getenv("EDGE_TTS_RATE", "+0%")
    volume = os.getenv("EDGE_TTS_VOLUME", "+0%")
    pitch = os.getenv("EDGE_TTS_PITCH", "+0Hz")

    with tempfile.NamedTemporaryFile(
        prefix="hr_reply_",
        suffix=".mp3",
        dir=tts_output_dir(),
        delete=False,
    ) as tmp:
        output_path = Path(tmp.name)

    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=rate,
            volume=volume,
            pitch=pitch,
        )
        await communicate.save(str(output_path))
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        raise SpeechSynthesisError(f"TTS failed: {exc}") from exc

    return {
        "audio_path": str(output_path),
        "voice": voice,
    }
