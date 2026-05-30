from __future__ import annotations

from app.service.history_service import TARGET_SCHEMA, build_agent_turn_payload
from app.shared_types.game_types import SessionState
from app.repositories.scene_repository import load_scene


def _minimal_session() -> SessionState:
    scene = load_scene("scene_001")
    return SessionState(
        session_id="sess_test",
        user_id="user_test",
        user_name="candidate",
        scene_id="scene_001",
        role_id="role_backend",
        hr_personality_id="hr_smiling_tiger",
        scene_context=scene,
    )


def test_target_schema_includes_hr_reply() -> None:
    assert "hr_reply" in TARGET_SCHEMA
    assert TARGET_SCHEMA["next_phase_hint"] == "text|end"


def test_build_turn_payload() -> None:
    session = _minimal_session()
    payload = build_agent_turn_payload(session, "salary talk")
    assert payload["player_text"] == "salary talk"
    assert payload["target_schema"] == TARGET_SCHEMA
    assert "history" in payload
    assert "negotiation_state" in payload
