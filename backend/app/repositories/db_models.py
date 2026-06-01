from __future__ import annotations

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TextSessionRecord(Base):
    __tablename__ = "text_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    user_name: Mapped[str] = mapped_column(String(128), default="候选人")
    hr_personality_id: Mapped[str] = mapped_column(String(64), default="hr_smiling_tiger")
    scene_id: Mapped[str] = mapped_column(String(64), default="scene_001")
    role_id: Mapped[str] = mapped_column(String(64), default="role_backend")
    status: Mapped[str] = mapped_column(String(32), default="ongoing", index=True)
    round_index: Mapped[int] = mapped_column(Integer, default=1)
    max_round: Mapped[int] = mapped_column(Integer, default=5)
    session_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class TextSessionResultRecord(Base):
    __tablename__ = "text_session_results"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    user_name: Mapped[str] = mapped_column(String(128), default="候选人")
    final_score: Mapped[int] = mapped_column(Integer, index=True)
    final_salary: Mapped[int] = mapped_column(Integer)
    grade: Mapped[str] = mapped_column(String(16))
    result_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class CardGameSessionRecord(Base):
    __tablename__ = "card_game_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    user_name: Mapped[str] = mapped_column(String(128), default="候选人")
    hr_personality_id: Mapped[str] = mapped_column(String(64), default="hr_smiling_tiger")
    status: Mapped[str] = mapped_column(String(32), default="ongoing", index=True)
    round_index: Mapped[int] = mapped_column(Integer, default=1)
    max_round: Mapped[int] = mapped_column(Integer, default=8)
    session_payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
