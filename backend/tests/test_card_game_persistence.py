from __future__ import annotations

from app.api.card_game_routes import create_card_session, get_card_session
from app.db import init_db, reset_db_engine


def _use_temp_db(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'card-test.db').as_posix()}")
    reset_db_engine()
    init_db()


def test_card_game_session_round_trip(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    created = create_card_session(
        {
            "user_id": "card_user_1",
            "user_name": "卡牌玩家",
            "hr_personality_id": "hr_robot",
        }
    )

    session_id = created.data["session"]["session_id"]
    loaded = get_card_session(session_id)

    assert loaded.data["session"]["session_id"] == session_id
    assert loaded.data["session"]["user_name"] == "卡牌玩家"
    assert loaded.data["session"]["hr_personality_id"] == "hr_robot"
