from __future__ import annotations

from sqlalchemy import desc, select

from app.db import db_session, init_db
from app.repositories.db_models import TextSessionRecord, TextSessionResultRecord
from app.shared_types.game_types import PersistResult, SessionState, SettleResult


def save_text_session(session_state: SessionState) -> SessionState:
    init_db()
    payload = session_state.model_dump(mode="json")
    with db_session() as session:
        record = session.get(TextSessionRecord, session_state.session_id)
        if record is None:
            record = TextSessionRecord(
                session_id=session_state.session_id,
                user_id=session_state.user_id,
                user_name=session_state.user_name,
                hr_personality_id=session_state.hr_personality_id,
                scene_id=session_state.scene_id,
                role_id=session_state.role_id,
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
            record.scene_id = session_state.scene_id
            record.role_id = session_state.role_id
            record.status = session_state.status
            record.round_index = session_state.round_index
            record.max_round = session_state.max_round
            record.session_payload = payload
        session.flush()
    return session_state


def get_text_session(session_id: str) -> SessionState | None:
    init_db()
    with db_session() as session:
        record = session.get(TextSessionRecord, session_id)
        if record is None:
            return None
        return SessionState.model_validate(record.session_payload)


def save_text_session_result(session_state: SessionState, settle_result: SettleResult) -> PersistResult:
    init_db()
    save_text_session(session_state)
    payload = settle_result.model_dump(mode="json")
    with db_session() as session:
        record = session.get(TextSessionResultRecord, session_state.session_id)
        if record is None:
            record = TextSessionResultRecord(
                session_id=session_state.session_id,
                user_id=session_state.user_id,
                user_name=session_state.user_name,
                final_score=settle_result.final_score,
                final_salary=settle_result.final_salary,
                grade=settle_result.grade,
                result_payload=payload,
            )
            session.add(record)
        else:
            record.user_id = session_state.user_id
            record.user_name = session_state.user_name
            record.final_score = settle_result.final_score
            record.final_salary = settle_result.final_salary
            record.grade = settle_result.grade
            record.result_payload = payload
        session.flush()
    return PersistResult(saved=True, user_id=session_state.user_id, session_id=session_state.session_id)


def list_leaderboard(*, limit: int = 50) -> list[dict[str, str | int]]:
    init_db()
    safe_limit = max(1, min(int(limit), 100))
    with db_session() as session:
        stmt = (
            select(TextSessionResultRecord)
            .order_by(desc(TextSessionResultRecord.final_score), desc(TextSessionResultRecord.created_at))
            .limit(safe_limit)
        )
        rows = session.execute(stmt).scalars().all()
        return [
            {
                "user_name": row.user_name or "候选人",
                "final_score": int(row.final_score),
                "final_salary": int(row.final_salary),
                "grade": str(row.grade),
                "created_at": str(row.created_at or ""),
            }
            for row in rows
        ]
