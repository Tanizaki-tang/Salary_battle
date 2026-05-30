from __future__ import annotations

from app.api.session_routes import create_session
from app.prompt.hr_personality import _PERSONALITY_REGISTRY


def test_create_session_random_personality_when_omitted():
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


def test_create_session_explicit_personality():
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
