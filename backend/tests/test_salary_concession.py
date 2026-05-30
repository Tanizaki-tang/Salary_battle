from __future__ import annotations

from app.modules.flow_controller.salary_concession import (
    compute_effective_salary_delta,
    get_concession_profile,
    k_above_initial_offer,
    marginal_raise_factor,
)
from app.modules.flow_controller.session_state_machine import advance_game_flow
from app.repositories.scene_repository import SCENE_REGISTRY
from app.shared_types.game_types import SessionState, TurnDelta, TurnResult


def _session(**overrides) -> SessionState:
    base = {
        "session_id": "sess_salary",
        "user_id": "u1",
        "scene_id": "scene_001",
        "role_id": "role_backend",
        "hr_personality_id": "hr_smiling_tiger",
        "round_index": 1,
        "max_round": 8,
        "hr_patience": 70,
        "info_exposure": 20,
        "current_salary_offer": 15000,
        "scene_context": SCENE_REGISTRY["scene_001"],
    }
    base.update(overrides)
    return SessionState(**base)


def _turn(requested: int) -> TurnResult:
    return TurnResult(
        hr_reply="ok",
        delta=TurnDelta(hr_patience=0, info_exposure=0, trap_count=0, salary_offer=requested),
        is_trap_hit=False,
        is_game_over=False,
        next_round=2,
    )


def test_newbie_raises_more_than_aggressive_at_same_level():
    newbie = _session(hr_personality_id="hr_newbie", current_salary_offer=17000)
    aggressive = _session(hr_personality_id="hr_aggressive", current_salary_offer=17000)
    assert compute_effective_salary_delta(newbie, 2000) > compute_effective_salary_delta(aggressive, 2000)


def test_marginal_difficulty_increases_with_k_above_initial():
    session = _session(hr_personality_id="hr_honest", current_salary_offer=15000)
    low = marginal_raise_factor(session)
    session.current_salary_offer = 20000
    high = marginal_raise_factor(session)
    assert low > high


def test_no_upper_cap_on_salary():
    session = _session(
        hr_personality_id="hr_newbie",
        current_salary_offer=28000,
    )
    next_state = advance_game_flow(session, _turn(5000))
    assert next_state.current_salary_offer > session.scene_context.salary_anchor.ideal_target


def test_personality_ordering_willingness():
    ids = ["hr_aggressive", "hr_robot", "hr_smiling_tiger", "hr_honest", "hr_newbie"]
    willingness = [get_concession_profile(pid).willingness for pid in ids]
    assert willingness == sorted(willingness)
