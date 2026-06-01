from __future__ import annotations

from app.api.session_routes import create_session, settle
from app.db import init_db, reset_db_engine
from app.prompt.hr_personality import _PERSONALITY_REGISTRY
from app.repositories.session_repository import get_text_session, list_leaderboard


def _use_temp_db(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    reset_db_engine()
    init_db()


def test_create_session_random_personality_when_omitted(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    init_db()
    resp = create_session(
        {
            "user_id": "user_test_random",
            "user_name": "测试",
            "scene_id": "scene_001",
            "role_id": "role_backend",
        }
    )
    data = resp.data
    assert data is not None
    pid = data["session"]["hr_personality_id"]
    assert pid in _PERSONALITY_REGISTRY
    meta = data["hr_personality_meta"]
    assert meta["personality_id"] == pid
    assert meta["name"]
    persisted = get_text_session(data["session"]["session_id"])
    assert persisted is not None
    assert persisted.user_id == "user_test_random"


def test_create_session_explicit_personality(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    init_db()
    resp = create_session(
        {
            "user_id": "user_test_explicit",
            "user_name": "测试",
            "scene_id": "scene_001",
            "role_id": "role_backend",
            "hr_personality_id": "hr_honest",
        }
    )
    data = resp.data
    assert data is not None
    assert data["session"]["hr_personality_id"] == "hr_honest"
    assert data["hr_personality_meta"]["name"] == "老实人型"


def test_settle_persists_result_and_leaderboard(monkeypatch, tmp_path):
    _use_temp_db(monkeypatch, tmp_path)
    init_db()
    created = create_session(
        {
            "user_id": "user_test_settle",
            "user_name": "落库验证",
            "scene_id": "scene_001",
            "role_id": "role_backend",
            "hr_personality_id": "hr_honest",
        }
    )
    session_id = created.data["session"]["session_id"]

    resp = settle(session_id)
    data = resp.data

    assert data["persist"]["saved"] is True
    leaderboard = list_leaderboard(limit=10)
    assert any(entry["user_name"] == "落库验证" for entry in leaderboard)
