from __future__ import annotations

from app.api.session_routes import create_session_data
from app.service.voice_game_point_service import apply_game_point_effects, build_voice_round_guidance, infer_game_point_hint
from app.shared_types.game_types import SessionState, TurnDelta


def _make_voice_session() -> SessionState:
    data = create_session_data(
        {
            "user_id": "voice_test_user",
            "user_name": "语音测试",
            "scene_id": "scene_001",
            "role_id": "role_backend",
            "interaction_mode": "voice",
            "hr_personality_id": "hr_honest",
        }
    )
    return SessionState.model_validate(data["session"])


def test_voice_round_guidance_contains_game_point_and_low_patience():
    session = _make_voice_session()
    session.hr_patience = 16

    guidance = build_voice_round_guidance(session)

    assert "谁先报价" in guidance
    assert "诚意" in guidance or "耐心" in guidance


def test_resolving_active_game_point_applies_bonus_and_hint():
    session = _make_voice_session()
    delta = TurnDelta(hr_patience=-2, info_exposure=3, trap_count=0, salary_offer=0, equity_ratio=0.0)
    player_text = "我想先了解这个岗位的预算区间和薪资结构，再决定要不要先报。"

    boosted = apply_game_point_effects(session, player_text=player_text, delta=delta)
    hint = infer_game_point_hint(
        session,
        hr_reply="你先说说你的期望薪资吧，我看看能不能帮你争取。",
        player_text=player_text,
        delta=boosted,
    )

    assert boosted.salary_offer >= 1000
    assert boosted.info_exposure <= -3
    assert hint is not None
    assert hint.point_id == "gp_salary_anchor"
    assert hint.status == "resolved"
