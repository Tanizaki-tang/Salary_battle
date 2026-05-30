from __future__ import annotations

from app.modules.voice_battle.opening_service import resolve_hr_opening
from app.repositories.scene_repository import load_scene
from app.shared_types.game_types import ConversationMessage, SessionState


def test_resolve_hr_opening_from_history() -> None:
    scene = load_scene("scene_001")
    session = SessionState(
        session_id="sess_open",
        user_id="user_open",
        user_name="Alice",
        scene_id="scene_001",
        scene_context=scene,
        conversation_history=[
            ConversationMessage(role="hr", content="Alice，你好，我们聊聊 offer。", round_index=0),
        ],
    )
    assert resolve_hr_opening(session) == "Alice，你好，我们聊聊 offer。"


def test_resolve_hr_opening_fallback_to_scene() -> None:
    scene = load_scene("scene_001")
    session = SessionState(
        session_id="sess_open2",
        user_id="user_open2",
        user_name="Bob",
        scene_id="scene_001",
        scene_context=scene,
    )
    opening = resolve_hr_opening(session)
    assert opening.startswith("Bob，")
    assert scene.opening_line in opening
