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
            user_name TEXT NOT NULL DEFAULT '候选人',
            final_score INTEGER NOT NULL,
            final_salary INTEGER NOT NULL,
            grade TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(game_session)")}
    if "user_name" not in columns:
        conn.execute("ALTER TABLE game_session ADD COLUMN user_name TEXT NOT NULL DEFAULT '候选人'")
    conn.commit()


def save_session_result(
    user_id: str,
    session_result: SettleResult,
    session_id: str,
    *,
    user_name: str = "候选人",
) -> PersistResult:
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
            "INSERT OR REPLACE INTO game_session (id, user_id, user_name, final_score, final_salary, grade) VALUES (?, ?, ?, ?, ?, ?)",
            (
                session_id,
                user_id,
                (user_name or "候选人").strip() or "候选人",
                session_result.final_score,
                session_result.final_salary,
                session_result.grade,
            ),
        )
        conn.commit()
        return PersistResult(saved=True, user_id=user_id, session_id=session_id)
    finally:
        conn.close()


def list_leaderboard(*, limit: int = 50) -> list[dict[str, str | int]]:
    conn = sqlite3.connect(DB_PATH)
    try:
        _ensure_tables(conn)
        cur = conn.execute(
            """
            SELECT user_name, final_score, final_salary, grade, created_at
            FROM game_session
            ORDER BY final_score DESC, created_at DESC
            LIMIT ?
            """,
            (max(1, min(int(limit), 100)),),
        )
        return [
            {
                "user_name": str(row[0] or "候选人"),
                "final_score": int(row[1]),
                "final_salary": int(row[2]),
                "grade": str(row[3]),
                "created_at": str(row[4] or ""),
            }
            for row in cur.fetchall()
        ]
    finally:
        conn.close()
