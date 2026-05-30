from __future__ import annotations

from app.shared_types.game_types import VoiceTurnPayload


def transcribe_audio(audio_payload: VoiceTurnPayload) -> dict:
    """
    输入:
    - audio_payload.audio_path: 音频文件路径
    - audio_payload.input_mode: 输入来源(默认 voice)

    输出:
    - {"transcript": str, "confidence": float}

    示例:
    - 输入 {"audio_path":"./demo.wav"} -> 输出 {"transcript":"我想确认薪资区间","confidence":0.9}
    """
    return {
        "transcript": "我想确认一下这个岗位的薪资区间和加班费。",
        "confidence": 0.9,
    }
