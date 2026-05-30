from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from app.prompt.character_prompt import build_system_prompt

try:
    from openai import OpenAI
except ImportError as exc:  # pragma: no cover - import guard for runtime
    raise ImportError("Missing dependency `openai`. Please install it in backend environment.") from exc


DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"
PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompt"
DEFAULT_PROMPT_FILE = "default_system_prompt.txt"


@dataclass(slots=True)
class LLMConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: float = 30.0


def load_config_from_env() -> LLMConfig:
    """
    从环境变量读取百炼配置。

    必需:
    - BAILIAN_API_KEY

    可选:
    - BAILIAN_BASE_URL (默认 DashScope OpenAI 兼容地址)
    - BAILIAN_MODEL (默认 qwen-plus)
    - BAILIAN_TIMEOUT_SECONDS (默认 30)
    """
    api_key = os.getenv("BAILIAN_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Environment variable `BAILIAN_API_KEY` is required.")
    base_url = os.getenv("BAILIAN_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    model = os.getenv("BAILIAN_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    timeout = float(os.getenv("BAILIAN_TIMEOUT_SECONDS", "30"))
    return LLMConfig(api_key=api_key, base_url=base_url, model=model, timeout=timeout)


def build_client(config: LLMConfig | None = None) -> OpenAI:
    cfg = config or load_config_from_env()
    return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url, timeout=cfg.timeout)


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 600,
    require_json: bool = False,
    config: LLMConfig | None = None,
) -> str:
    """
    通用聊天接口（百炼 OpenAI 兼容）。

    输入:
    - messages: [{"role":"system|user|assistant","content":"..."}]
    - require_json: True 时强制返回 JSON 字符串

    输出:
    - 模型文本输出（字符串）
    """
    cfg = config or load_config_from_env()
    client = build_client(cfg)
    kwargs: dict[str, Any] = {
        "model": model or cfg.model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if require_json:
        kwargs["response_format"] = {"type": "json_object"}

    completion = client.chat.completions.create(**kwargs)
    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("LLM returned empty content.")
    return content


def chat_completion_stream(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 600,
    config: LLMConfig | None = None,
) -> Iterator[str]:
    """
    流式聊天接口（百炼 OpenAI 兼容）。

    输入:
    - messages: [{"role":"system|user|assistant","content":"..."}]

    输出:
    - 逐片段产出文本 Iterator[str]

    用法示例:
    >>> for chunk in chat_completion_stream(messages):
    ...     print(chunk, end="")
    """
    cfg = config or load_config_from_env()
    client = build_client(cfg)
    stream = client.chat.completions.create(
        model=model or cfg.model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )

    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        piece = getattr(delta, "content", None)
        if piece:
            yield piece


def llm_state_adjustment(
    *,
    scene_context: dict[str, Any],
    session_state: dict[str, Any],
    player_text: str,
    base_turn_result: dict[str, Any],
    model: str | None = None,
    config: LLMConfig | None = None,
) -> dict[str, Any]:
    """
    用于“回合状态修正”的专用接口。

    输入:
    - scene_context: 当前 scene 的规则与人设
    - session_state: 当前会话状态
    - player_text: 玩家本轮输入文本
    - base_turn_result: text/voice 合同产出的基础回合结果

    输出(JSON):
    {
      "hr_reply": "string",
      "inferred_strategy": "strong_push|probe|concede|counter_pressure|law_citation|trap_detected|chitchat",
      "delta_hr_patience": int,
      "delta_info_exposure": int,
      "delta_trap_count": int,
      "delta_salary_offer": int,
      "delta_equity_ratio": float,
      "delta_law_citation_count": int,
      "delta_misjudge_count": int,
      "trap_id": "A|B|C|D|E|null",
      "should_end": bool,
      "next_phase_hint": "text|voice|end",
      "reason": "..."
    }
    """
    system_prompt = _load_scene_prompt(scene_context)
    user_payload = {
        "scene_context": scene_context,
        "session_state": session_state,
        "player_text": player_text,
        "base_turn_result": base_turn_result,
        "target_schema": {
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
        },
    }
    content = chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        model=model,
        require_json=True,
        config=config,
    )

    parsed = json.loads(content)
    return {
        "hr_reply": str(parsed.get("hr_reply", "")),
        "inferred_strategy": str(parsed.get("inferred_strategy", "probe")),
        "delta_hr_patience": _clamp_int(parsed.get("delta_hr_patience", 0), -15, 10),
        "delta_info_exposure": _clamp_int(parsed.get("delta_info_exposure", 0), -12, 18),
        "delta_trap_count": _clamp_int(parsed.get("delta_trap_count", 0), 0, 1),
        "delta_salary_offer": _clamp_int(parsed.get("delta_salary_offer", 0), 0, 5000),
        "delta_equity_ratio": _clamp_float(parsed.get("delta_equity_ratio", 0.0), 0.0, 0.2),
        "delta_law_citation_count": _clamp_int(parsed.get("delta_law_citation_count", 0), 0, 1),
        "delta_misjudge_count": _clamp_int(parsed.get("delta_misjudge_count", 0), 0, 1),
        "trap_id": _safe_trap_id(parsed.get("trap_id")),
        "should_end": bool(parsed.get("should_end", False)),
        "next_phase_hint": _safe_phase(parsed.get("next_phase_hint", "text")),
        "reason": str(parsed.get("reason", "")),
    }


def _clamp_int(value: Any, min_value: int, max_value: int) -> int:
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        return 0
    return max(min_value, min(max_value, ivalue))


def _safe_phase(value: Any) -> str:
    phase = str(value).lower()
    if phase in {"text", "voice", "end"}:
        return phase
    return "text"


def _clamp_float(value: Any, min_value: float, max_value: float) -> float:
    try:
        fvalue = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(min_value, min(max_value, fvalue))


def _safe_trap_id(value: Any) -> str | None:
    trap = str(value).strip().upper()
    if trap in {"A", "B", "C", "D", "E"}:
        return trap
    return None


def _load_scene_prompt(scene_context: dict[str, Any]) -> str:
    meta = scene_context.get("meta", {}) if isinstance(scene_context, dict) else {}
    scene_id = str(meta.get("scene_id", "scene_001")).strip() or "scene_001"
    base_file = PROMPT_DIR / DEFAULT_PROMPT_FILE
    if base_file.exists():
        base_prompt = base_file.read_text(encoding="utf-8")
    else:
        base_prompt = (
            "你是谈判游戏状态评估器。根据场景规则与玩家输入，输出状态修正JSON。"
            "只返回 JSON，不要额外文本。"
            "必须先判断玩家意图分类，然后生成HR回复，并给出状态增量。"
            "数值约束: delta_hr_patience[-15,10], delta_info_exposure[-12,18], delta_trap_count[0,1], "
            "delta_salary_offer[0,5000], delta_equity_ratio[0,0.2], delta_law_citation_count[0,1], delta_misjudge_count[0,1]。"
        )
    return build_system_prompt(base_prompt=base_prompt, scene_id=scene_id)
