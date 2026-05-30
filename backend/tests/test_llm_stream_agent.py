from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from app.modules.agent.hr_negotiation_agent import HrNegotiationAgent
from app.modules.agent.tools.voice_battle_tool import VoiceBattleTool
from app.service.history_service import STATE_TARGET_SCHEMA, build_agent_reply_payload, build_agent_state_payload
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


def test_state_schema_excludes_hr_reply() -> None:
    assert "hr_reply" not in STATE_TARGET_SCHEMA
    assert "delta_hr_patience" in STATE_TARGET_SCHEMA


def test_build_stream_payloads() -> None:
    session = _minimal_session()
    reply_payload = build_agent_reply_payload(session, "salary talk")
    state_payload = build_agent_state_payload(session, "salary talk", "budget is tight.")
    assert reply_payload["player_text"] == "salary talk"
    assert "target_schema" not in reply_payload
    assert state_payload["hr_reply"] == "budget is tight."
    assert state_payload["target_schema"] == STATE_TARGET_SCHEMA


def test_decide_stream_emits_tokens_before_state_invoke() -> None:
    session = _minimal_session()
    agent = HrNegotiationAgent(MagicMock(spec=VoiceBattleTool))
    events: list[str] = []

    state_json = {
        "inferred_strategy": "probe",
        "delta_hr_patience": -2,
        "delta_info_exposure": 3,
        "delta_trap_count": 0,
        "delta_salary_offer": 0,
        "delta_equity_ratio": 0.0,
        "delta_law_citation_count": 0,
        "delta_misjudge_count": 0,
        "trap_id": None,
        "should_end": False,
        "next_phase_hint": "voice",
        "reason": "test",
    }

    def stream_side_effect(**kwargs):
        on_delta = kwargs.get("on_delta")
        if on_delta:
            on_delta("hello, ")
            on_delta("let us talk salary.")
        return "hello, let us talk salary."

    with patch.object(agent, "_stream_hr_reply", side_effect=stream_side_effect):
        with patch.object(agent, "_invoke_state_delta", return_value=state_json):
            decision = agent.decide_voice_text_stream(session, "salary talk", on_delta=events.append)

    assert events == ["hello, ", "let us talk salary."]
    assert "hello" in decision.hr_reply
    assert decision.delta.hr_patience == -2
    assert decision.next_phase_hint == "voice"
