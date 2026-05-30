from __future__ import annotations

from typing import Any, Literal

from app.shared_types.game_types import ConversationMessage, SessionState

Role = Literal["hr", "player", "system"]

# 场景/人格等静态信息已在 system prompt 中，不再重复传给 LLM。
_SESSION_STATIC_KEYS = frozenset({"scene_context", "user_id", "session_id", "status"})

TARGET_SCHEMA: dict[str, str] = {
    "hr_reply": "string",
    "inferred_strategy": "string",
    "delta_hr_patience": "int",
    "delta_info_exposure": "int",
    "delta_trap_count": "int",
    "delta_salary_offer": "int",
    "delta_equity_ratio": "float",
    "delta_law_citation_count": "int",
    "delta_misjudge_count": "int",
    "trap_id": "string|null",
    "should_end": "bool",
    "next_phase_hint": "text|voice|end",
    "reason": "string",
}


def _as_session_state(session_state: SessionState | dict[str, Any]) -> SessionState:
    if isinstance(session_state, SessionState):
        return session_state
    return SessionState.model_validate(session_state)


def _normalize_messages(
    messages: list[ConversationMessage] | list[dict[str, Any]],
) -> list[ConversationMessage]:
    normalized: list[ConversationMessage] = []
    for item in messages:
        if isinstance(item, ConversationMessage):
            normalized.append(item)
        else:
            normalized.append(ConversationMessage.model_validate(item))
    return normalized


def format_history_turn(message: ConversationMessage) -> dict[str, str | int]:
    """单条对话压缩为 role + text + round。"""
    return {
        "round": message.round_index,
        "role": message.role,
        "text": message.content.strip(),
    }


def extract_conversation_history(
    session_state: SessionState | dict[str, Any],
    *,
    max_turns: int = 20,
) -> dict[str, Any]:
    """提取对话历史，并单独列出近期 HR 回复供反重复参考。"""
    state = _as_session_state(session_state)
    messages = _normalize_messages(state.conversation_history)
    if max_turns > 0:
        messages = messages[-max_turns:]

    turns = [format_history_turn(msg) for msg in messages if msg.content.strip()]
    recent_hr_replies = [turn["text"] for turn in turns if turn["role"] == "hr"][-4:]

    return {
        "turns": turns,
        "turn_count": len(turns),
        "recent_hr_replies": recent_hr_replies,
    }


def extract_negotiation_state(session_state: SessionState | dict[str, Any]) -> dict[str, Any]:
    """提取本轮决策所需的动态状态，去掉 scene_context 等静态字段。"""
    state = _as_session_state(session_state)
    payload = state.model_dump(exclude=_SESSION_STATIC_KEYS)
    payload.pop("conversation_history", None)
    return payload


def build_agent_turn_payload(
    session_state: SessionState | dict[str, Any],
    player_text: str,
    base_turn_result: dict[str, Any] | None = None,
    *,
    max_history_turns: int = 20,
    target_schema: dict[str, str] | None = None,
) -> dict[str, Any]:
    """组装交给 Agent LLM 的精简 user payload。"""
    history = extract_conversation_history(session_state, max_turns=max_history_turns)
    negotiation_state = extract_negotiation_state(session_state)

    payload: dict[str, Any] = {
        "instruction": (
            "场景与人格已在 system prompt 中，请勿重复引用静态背景。"
            "先阅读 history.turns 与 history.recent_hr_replies，"
            "确保 hr_reply 与近期 HR 话术明显不同，再输出 JSON。"
        ),
        "player_text": player_text.strip(),
        "history": history,
        "negotiation_state": negotiation_state,
        "target_schema": target_schema or TARGET_SCHEMA,
    }
    if base_turn_result is not None:
        payload["base_turn_result"] = base_turn_result
    return payload
