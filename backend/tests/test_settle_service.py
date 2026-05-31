from __future__ import annotations

from app.modules.flow_controller.settle_service import build_review_tip, settle_session
from app.repositories.scene_repository import SCENE_REGISTRY
from app.shared_types.game_types import SessionState


def _session(**overrides) -> SessionState:
    base = {
        "session_id": "sess_test",
        "user_id": "u1",
        "scene_id": "scene_001",
        "role_id": "role_backend",
        "round_index": 5,
        "max_round": 8,
        "hr_patience": 60,
        "info_exposure": 25,
        "current_salary_offer": 20000,
        "identified_traps": ["A", "B"],
        "strategy_history": ["probe", "strong_push", "counter_pressure"],
        "scene_context": SCENE_REGISTRY["scene_001"],
    }
    base.update(overrides)
    return SessionState(**base)


def test_review_tip_high_score_band():
    session = _session(current_salary_offer=24000, identified_traps=["A", "B", "C", "D"])
    result = settle_session(session)
    assert result.final_score >= 80
    assert "老练" in result.review_tip or "出色" in result.review_tip or "追问" in result.review_tip


def test_review_tip_high_exposure_override():
    session = _session(info_exposure=85, current_salary_offer=18000, identified_traps=[])
    result = settle_session(session)
    assert "暴露" in result.review_tip


def test_review_tip_low_score_band():
    session = _session(
        current_salary_offer=9000,
        info_exposure=70,
        identified_traps=[],
        strategy_history=["concede"],
        hr_patience=15,
        misjudge_count=0,
    )
    result = settle_session(session)
    assert result.final_score < 60
    assert len(result.review_tip) >= 8


def test_settle_result_includes_breakdown_and_offer():
    session = _session(current_salary_offer=22000, identified_traps=["B", "C", "D"])
    result = settle_session(session)
    assert result.title
    assert result.breakdown is not None
    assert 0 <= result.breakdown.dq <= 100
    assert result.offer is not None
    assert result.offer.overtime_policy == "单独计算"
    assert result.stats is not None
    assert result.stats.traps_identified == 3
    assert "五险一金模糊" in result.stats.trap_labels
    assert "加班费打包" in result.stats.trap_labels
    assert result.summary


def test_build_review_tip_no_traps():
    session = _session(identified_traps=[], info_exposure=30, current_salary_offer=16000)
    tip = build_review_tip(final_score=72, dq=55, td=20, wh=60, si=50, session_state=session)
    assert "陷阱" in tip
