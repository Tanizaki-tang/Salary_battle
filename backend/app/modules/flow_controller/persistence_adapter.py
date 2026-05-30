from __future__ import annotations

import sqlite3
from pathlib import Path

from app.shared_types.game_types import PersistResult, SettleResult


DB_PATH = Path(__file__).resolve().parents[3] / "app.db"


def _ensure_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS game_session (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            final_score INTEGER NOT NULL,
            final_salary INTEGER NOT NULL,
            grade TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def save_session_result(user_id: str, session_result: SettleResult, session_id: str) -> PersistResult:
    """
    输入:
    - user_id: 用户ID
    - session_result: 结算结果
    - session_id: 对局ID

    输出:
    - PersistResult: 落库成功标记及主键信息

    示例:
    - 输入 user_id='u1', final_score=84
    - 输出 {"saved":true,"user_id":"u1","session_id":"sess_001"}
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        _ensure_tables(conn)
        conn.execute(
            "INSERT OR REPLACE INTO game_session (id, user_id, final_score, final_salary, grade) VALUES (?, ?, ?, ?, ?)",
            (session_id, user_id, session_result.final_score, session_result.final_salary, session_result.grade),
        )
        conn.commit()
        return PersistResult(saved=True, user_id=user_id, session_id=session_id)
    finally:
        conn.close()
