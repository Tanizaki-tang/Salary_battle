from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.orchestrators.game_flow_orchestrator import GameFlowOrchestrator
from app.shared_types.game_types import SessionState, TextTurnPayload


def run_demo() -> dict:
    orchestrator = GameFlowOrchestrator()
    session = SessionState(session_id="sess_demo_001", user_id="user_demo")
    session, turn_1 = orchestrator.run_text_turn(session, TextTurnPayload(strategy="probe"))
    session, turn_2 = orchestrator.run_text_turn(session, TextTurnPayload(strategy="counter_pressure"))
    settle_result, persist_result = orchestrator.settle_and_persist(session)
    return {
        "turn_1": turn_1.model_dump(),
        "turn_2": turn_2.model_dump(),
        "settle": settle_result.model_dump(),
        "persist": persist_result.model_dump(),
    }


if __name__ == "__main__":
    print(run_demo())
