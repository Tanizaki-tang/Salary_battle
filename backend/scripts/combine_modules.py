from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.flow_controller.persistence_adapter import save_session_result
from app.modules.flow_controller.session_state_machine import advance_game_flow
from app.modules.flow_controller.settle_service import settle_session
from app.modules.text_battle.text_battle_engine import TextBattleEngine
from app.modules.voice_battle.voice_battle_engine import VoiceBattleEngine


def validate_contracts() -> dict:
    text_engine = TextBattleEngine()
    voice_engine = VoiceBattleEngine()
    checks = {
        "run_text_turn": callable(getattr(text_engine, "run_text_turn", None)),
        "run_voice_turn": callable(getattr(voice_engine, "run_voice_turn", None)),
        "advance_game_flow": callable(advance_game_flow),
        "settle_session": callable(settle_session),
        "save_session_result": callable(save_session_result),
    }
    return checks


if __name__ == "__main__":
    result = validate_contracts()
    print(result)
    if not all(result.values()):
        raise SystemExit(1)
