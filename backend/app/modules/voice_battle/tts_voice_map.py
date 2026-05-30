from __future__ import annotations

PERSONALITY_TTS_SID: dict[str, int] = {
    "hr_newbie": 0,
    "hr_robot": 1,
    "hr_aggressive": 2,
    "hr_honest": 3,
    "hr_smiling_tiger": 4,
}

DEFAULT_TTS_SID = 0


def resolve_tts_speaker_id(personality_id: str | None) -> int:
    pid = (personality_id or "").strip()
    if not pid:
        return DEFAULT_TTS_SID
    return PERSONALITY_TTS_SID.get(pid, DEFAULT_TTS_SID)
