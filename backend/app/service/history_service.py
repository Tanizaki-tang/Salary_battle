from __future__ import annotations

from typing import Any, Literal

from app.prompt.dialogue_style import SALARY_UNIT_RULES
from app.prompt.salary_format import enrich_negotiation_salary_fields
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
    "next_phase_hint": "text|end",
    "reason": "string",
}

STATE_TARGET_SCHEMA: dict[str, str] = {
    key: value for key, value in TARGET_SCHEMA.items() if key != "hr_reply"
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
    anchor = state.scene_context.salary_anchor
    payload["salary_anchor"] = {
        "legal_floor": anchor.legal_floor,
        "market_fair": anchor.market_fair,
        "ideal_target": anchor.ideal_target,
        "hr_initial_offer": anchor.hr_initial_offer,
    }
    return enrich_negotiation_salary_fields(payload)


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
            "若 recent_hr_replies 已明确录用意愿（offer/决定录用/欢迎加入等），"
            "禁止在本轮 hr_reply 或 should_end/reason 中输出未录用、谈崩、收回 offer 等矛盾结果。"
            f"{SALARY_UNIT_RULES}"
        ),
        "player_text": player_text.strip(),
        "history": history,
        "negotiation_state": negotiation_state,
        "target_schema": target_schema or TARGET_SCHEMA,
    }
    if base_turn_result is not None:
        payload["base_turn_result"] = base_turn_result
    return payload


def build_agent_reply_payload(
    session_state: SessionState | dict[str, Any],
    player_text: str,
    *,
    max_history_turns: int = 20,
) -> dict[str, Any]:
    """阶段 1：流式口语回复，仅传对话上下文。"""
    history = extract_conversation_history(session_state, max_turns=max_history_turns)
    negotiation_state = extract_negotiation_state(session_state)
    return {
        "instruction": (
            "场景与人格已在 system prompt 中。"
            "阅读 history.recent_hr_replies，确保本轮口语回复与近期 HR 话术明显不同。"
            "只输出你要对候选人说的话，2-4 句，口语化。"
            f"{SALARY_UNIT_RULES}"
        ),
        "player_text": player_text.strip(),
        "history": history,
        "negotiation_state": negotiation_state,
    }


def build_agent_state_payload(
    session_state: SessionState | dict[str, Any],
    player_text: str,
    hr_reply: str,
    base_turn_result: dict[str, Any] | None = None,
    *,
    max_history_turns: int = 20,
) -> dict[str, Any]:
    """阶段 2：根据玩家输入与 HR 已说回复，输出状态增量 JSON。"""
    history = extract_conversation_history(session_state, max_turns=max_history_turns)
    negotiation_state = extract_negotiation_state(session_state)
    payload: dict[str, Any] = {
        "instruction": (
            "HR 回复已生成，请勿改写 hr_reply。"
            "根据玩家输入、HR 回复与谈判状态，输出状态修正 JSON，只返回 JSON。"
        ),
        "player_text": player_text.strip(),
        "hr_reply": hr_reply.strip(),
        "history": history,
        "negotiation_state": negotiation_state,
        "target_schema": STATE_TARGET_SCHEMA,
    }
    if base_turn_result is not None:
        payload["base_turn_result"] = base_turn_result
    return payload
