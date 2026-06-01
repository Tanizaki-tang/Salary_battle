from __future__ import annotations
from app.repositories.session_repository import list_leaderboard, save_text_session_result
from app.shared_types.game_types import PersistResult, SessionState, SettleResult


def save_session_result(
    session_state: SessionState,
    session_result: SettleResult,
) -> PersistResult:
    return save_text_session_result(session_state, session_result)
