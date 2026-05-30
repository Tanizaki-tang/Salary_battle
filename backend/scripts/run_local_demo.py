from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.flow_controller.orchestrator import GameFlowOrchestrator
from app.repositories.scene_repository import load_scene
from app.shared_types.game_types import SessionState, TextTurnPayload


def run_demo() -> dict:
    orchestrator = GameFlowOrchestrator()
    scene_context = load_scene("scene_001")
    session = SessionState(
        session_id="sess_demo_001",
        user_id="user_demo",
        role_id="role_backend",
        scene_id="scene_001",
        max_round=scene_context.initial_state.max_round,
        hr_patience=scene_context.initial_state.hr_patience,
        info_exposure=scene_context.initial_state.info_exposure,
        trap_count=scene_context.initial_state.trap_count,
        scene_context=scene_context,
    )
    session, turn_1, flow_1 = orchestrator.run_text_turn(session, TextTurnPayload(strategy="probe"))
    session, turn_2, flow_2 = orchestrator.run_text_turn(session, TextTurnPayload(strategy="counter_pressure"))
    settle_result, persist_result = orchestrator.settle_and_persist(session)
    return {
        "turn_1": turn_1.model_dump(),
        "flow_1": flow_1.model_dump(),
        "turn_2": turn_2.model_dump(),
        "flow_2": flow_2.model_dump(),
        "settle": settle_result.model_dump(),
        "persist": persist_result.model_dump(),
    }


if __name__ == "__main__":
    print(run_demo())
