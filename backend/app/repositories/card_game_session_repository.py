from __future__ import annotations

from app.db import db_session, init_db
from app.repositories.db_models import CardGameSessionRecord
from app.shared_types.card_game_types import CardGameState


def save_card_session(session_state: CardGameState) -> CardGameState:
    init_db()
    payload = session_state.model_dump(mode="json")
    with db_session() as session:
        record = session.get(CardGameSessionRecord, session_state.session_id)
        if record is None:
            record = CardGameSessionRecord(
                session_id=session_state.session_id,
                user_id=session_state.user_id,
                user_name=session_state.user_name,
                hr_personality_id=session_state.hr_personality_id,
                status=session_state.status,
                round_index=session_state.round_index,
                max_round=session_state.max_round,
                session_payload=payload,
            )
            session.add(record)
        else:
            record.user_id = session_state.user_id
            record.user_name = session_state.user_name
            record.hr_personality_id = session_state.hr_personality_id
            record.status = session_state.status
            record.round_index = session_state.round_index
            record.max_round = session_state.max_round
            record.session_payload = payload
        session.flush()
    return session_state


def get_card_session(session_id: str) -> CardGameState | None:
    init_db()
    with db_session() as session:
        record = session.get(CardGameSessionRecord, session_id)
        if record is None:
            return None
        return CardGameState.model_validate(record.session_payload)
