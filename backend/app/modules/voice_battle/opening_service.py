from __future__ import annotations

from app.shared_types.game_types import SessionState


def resolve_hr_opening(session: SessionState) -> str:
    """取本会话 HR 开场白（优先 conversation_history 中首条 HR 消息）。"""
    for msg in session.conversation_history:
        if msg.role == "hr" and msg.content.strip():
            return msg.content.strip()
    name = (session.user_name or "").strip() or "候选人"
    return f"{name}，{session.scene_context.opening_line}"
