from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]
from langchain_openai import ChatOpenAI  # pyright: ignore[reportMissingImports]
from openai import NotFoundError  # pyright: ignore[reportMissingImports]

from app.prompt.character_prompt import build_system_prompt
from app.prompt.dialogue_style import clamp_hr_reply
from app.service.history_service import build_agent_turn_payload
from app.service.llm_service import DEFAULT_MODEL, LLMConfig, llm_latency_enabled, load_config_from_env
from app.shared_types.game_types import AgentToolCallTrace, AgentTurnDecision, SessionState, TurnDelta

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompt"
DEFAULT_PROMPT_FILE = "default_system_prompt.txt"
logger = logging.getLogger(__name__)


class HrNegotiationAgent:
    def __init__(self) -> None:
        self._llm: ChatOpenAI | None = None
        self._llm_config: LLMConfig | None = None
        self._active_model: str | None = None

    def decide_text_turn(self, session_state: SessionState, player_text: str) -> AgentTurnDecision:
        text = (player_text or "").strip()
        if not text:
            text = "我希望了解这份 offer 的组成和边界。"
        return self._decide(session_state=session_state, player_text=text, traces=[])

    def _decide(self, *, session_state: SessionState, player_text: str, traces: list[AgentToolCallTrace]) -> AgentTurnDecision:
        base_result = self._base_turn_result(session_state)
        call_started = time.perf_counter()
        logger.info(
            "LLM_CALL_START session_id=%s scene_id=%s round=%s text_len=%s tool_traces=%s",
            session_state.session_id,
            session_state.scene_id,
            session_state.round_index,
            len(player_text),
            len(traces),
        )
        try:
            llm = self._invoke_langchain_llm(
                session_state=session_state,
                player_text=player_text,
                base_turn_result=base_result,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - call_started) * 1000)
            logger.exception(
                "LLM_CALL_FAILED session_id=%s scene_id=%s round=%s elapsed_ms=%s error=%s",
                session_state.session_id,
                session_state.scene_id,
                session_state.round_index,
                elapsed_ms,
                type(exc).__name__,
            )
            return self._safe_default_decision(session_state=session_state, player_text=player_text, traces=traces)
        elapsed_ms = int((time.perf_counter() - call_started) * 1000)
        next_phase_hint_raw = str(llm.get("next_phase_hint", "text"))
        inferred_strategy = str(llm.get("inferred_strategy", "probe"))
        hr_reply_raw = clamp_hr_reply(
            str(llm.get("hr_reply", base_result["hr_reply"])) or str(base_result["hr_reply"])
        )
        hr_patience_delta = self._clamp_int(llm.get("delta_hr_patience", 0), -15, 10)
        info_exposure_delta = self._clamp_int(llm.get("delta_info_exposure", 0), -12, 18)
        trap_count_delta = self._clamp_int(llm.get("delta_trap_count", 0), 0, 1)
        salary_offer_delta = self._clamp_int(llm.get("delta_salary_offer", 0), 0, 5000)
        equity_ratio_delta = self._clamp_float(llm.get("delta_equity_ratio", 0.0), 0.0, 0.2)
        law_citation_delta = self._clamp_int(llm.get("delta_law_citation_count", 0), 0, 1)
        misjudge_delta = self._clamp_int(llm.get("delta_misjudge_count", 0), 0, 1)
        trap_id = self._safe_trap_id(llm.get("trap_id"))
        should_end = bool(llm.get("should_end", False))
        decision_reason = str(llm.get("reason", "agent_decision"))

        logger.info(
            "LLM_CALL_OK session_id=%s scene_id=%s round=%s elapsed_ms=%s next_phase_hint=%s strategy=%s",
            session_state.session_id,
            session_state.scene_id,
            session_state.round_index,
            elapsed_ms,
            next_phase_hint_raw,
            inferred_strategy,
        )

        return AgentTurnDecision(
            hr_reply=self._address_player(session_state.user_name, hr_reply_raw),
            inferred_strategy=inferred_strategy,
            delta=TurnDelta(
                hr_patience=hr_patience_delta,
                info_exposure=info_exposure_delta,
                trap_count=trap_count_delta,
                salary_offer=salary_offer_delta,
                equity_ratio=equity_ratio_delta,
                law_citation_count=law_citation_delta,
                misjudge_count=misjudge_delta,
            ),
            trap_id=trap_id,
            next_phase_hint=self._safe_phase(next_phase_hint_raw),
            should_end=should_end,
            reason=decision_reason,
            tool_trace=traces,
            player_text_used=player_text,
        )

    def _invoke_langchain_llm(
        self,
        *,
        session_state: SessionState,
        player_text: str,
        base_turn_result: dict[str, Any],
    ) -> dict[str, Any]:
        t0 = time.perf_counter()
        system_prompt = self._load_scene_prompt(
            session_state.scene_id,
            session_state.hr_personality_id,
        )
        t1 = time.perf_counter()
        user_payload = build_agent_turn_payload(
            session_state=session_state,
            player_text=player_text,
            base_turn_result=base_turn_result,
        )
        t2 = time.perf_counter()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(user_payload, ensure_ascii=False)),
        ]
        llm = self._get_llm()
        t3 = time.perf_counter()
        try:
            response = llm.invoke(messages)
        except NotFoundError as exc:
            if not self._is_model_not_found(exc):
                raise
            if self._active_model == DEFAULT_MODEL:
                raise
            logger.warning(
                "LLM_MODEL_FALLBACK from=%s to=%s reason=model_not_found",
                self._active_model,
                DEFAULT_MODEL,
            )
            llm = self._build_llm(model=DEFAULT_MODEL, temperature=0.1)
            self._llm = llm
            self._active_model = DEFAULT_MODEL
            response = llm.invoke(messages)
        t4 = time.perf_counter()
        content = response.content if isinstance(response.content, str) else str(response.content)
        parsed = self._parse_json_content(content)
        t5 = time.perf_counter()
        if llm_latency_enabled():
            logger.info(
                "LLM_LATENCY session_id=%s scene_id=%s round=%s model=%s prompt_ms=%.1f payload_ms=%.1f invoke_ms=%.1f parse_ms=%.1f",
                session_state.session_id,
                session_state.scene_id,
                session_state.round_index,
                self._active_model,
                (t1 - t0) * 1000,
                (t2 - t1) * 1000,
                (t4 - t3) * 1000,
                (t5 - t4) * 1000,
            )
        return {
            "hr_reply": str(parsed.get("hr_reply", "")),
            "inferred_strategy": str(parsed.get("inferred_strategy", "probe")),
            "delta_hr_patience": self._clamp_int(parsed.get("delta_hr_patience", 0), -15, 10),
            "delta_info_exposure": self._clamp_int(parsed.get("delta_info_exposure", 0), -12, 18),
            "delta_trap_count": self._clamp_int(parsed.get("delta_trap_count", 0), 0, 1),
            "delta_salary_offer": self._clamp_int(parsed.get("delta_salary_offer", 0), 0, 5000),
            "delta_equity_ratio": self._clamp_float(parsed.get("delta_equity_ratio", 0.0), 0.0, 0.2),
            "delta_law_citation_count": self._clamp_int(parsed.get("delta_law_citation_count", 0), 0, 1),
            "delta_misjudge_count": self._clamp_int(parsed.get("delta_misjudge_count", 0), 0, 1),
            "trap_id": self._safe_trap_id(parsed.get("trap_id")),
            "should_end": bool(parsed.get("should_end", False)),
            "next_phase_hint": self._safe_phase(str(parsed.get("next_phase_hint", "text"))),
            "reason": str(parsed.get("reason", "")),
        }

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        return json.loads(text)

    def _load_scene_prompt(
        self,
        scene_id: str,
        personality_id: str | None = None,
    ) -> str:
        base_file = PROMPT_DIR / DEFAULT_PROMPT_FILE
        if base_file.exists():
            base_prompt = base_file.read_text(encoding="utf-8")
        else:
            base_prompt = (
                "你是谈判游戏状态评估器。根据场景规则与玩家输入，输出状态修正JSON。"
                "只返回 JSON，不要额外文本。"
                "必须先判断玩家意图分类，然后生成HR回复，并给出状态增量。"
                "hr_reply 为 Boss 直聘式短聊：1~2句、≤80字，口语自然，禁止长段。"
                "若近期 HR 已明确录用意愿（offer/决定录用/欢迎加入等），禁止输出未录用、谈崩、收回 offer 等矛盾话术；"
                "should_end=true 表示进入结算时，reason 不得与录用意愿矛盾。"
                "数值约束: delta_hr_patience[-15,10], delta_info_exposure[-12,18], delta_trap_count[0,1], "
                "delta_salary_offer[0,5000], delta_equity_ratio[0,0.2], delta_law_citation_count[0,1], delta_misjudge_count[0,1]。"
            )
        return build_system_prompt(
            base_prompt=base_prompt,
            scene_id=scene_id,
            personality_id=personality_id,
        )

    def _get_llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm_config = load_config_from_env()
            self._active_model = self._llm_config.model
            self._llm = self._build_llm(model=self._active_model, temperature=0.1)
        return self._llm

    def _build_llm(self, model: str, *, temperature: float) -> ChatOpenAI:
        cfg = self._llm_config or load_config_from_env()
        self._llm_config = cfg
        return ChatOpenAI(
            api_key=cfg.api_key,
            base_url=cfg.base_url,
            model=model,
            temperature=temperature,
            timeout=cfg.timeout,
        )

    @staticmethod
    def _is_model_not_found(exc: Exception) -> bool:
        msg = str(exc).lower()
        return "model_not_found" in msg or "does not exist" in msg

    @staticmethod
    def _clamp_int(value: Any, min_value: int, max_value: int) -> int:
        try:
            ivalue = int(value)
        except (TypeError, ValueError):
            return 0
        return max(min_value, min(max_value, ivalue))

    @staticmethod
    def _clamp_float(value: Any, min_value: float, max_value: float) -> float:
        try:
            fvalue = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(min_value, min(max_value, fvalue))

    @staticmethod
    def _safe_trap_id(value: Any) -> str | None:
        trap = str(value).strip().upper()
        if trap in {"A", "B", "C", "D", "E"}:
            return trap
        return None

    def _base_turn_result(self, session_state: SessionState) -> dict:
        return {
            "hr_reply": session_state.scene_context.tone_map["probe"],
            "delta": {
                "hr_patience": -1,
                "info_exposure": 2,
                "trap_count": 0,
                "salary_offer": 0,
                "equity_ratio": 0.0,
                "law_citation_count": 0,
                "misjudge_count": 0,
            },
            "is_trap_hit": False,
            "is_game_over": False,
            "next_round": min(session_state.round_index + 1, session_state.max_round),
        }

    def _safe_default_decision(
        self, *, session_state: SessionState, player_text: str, traces: list[AgentToolCallTrace]
    ) -> AgentTurnDecision:
        return AgentTurnDecision(
            hr_reply=self._address_player(session_state.user_name, session_state.scene_context.tone_map["probe"]),
            inferred_strategy="probe",
            delta=TurnDelta(hr_patience=-1, info_exposure=2, trap_count=0),
            trap_id=None,
            next_phase_hint="text",
            should_end=False,
            reason="agent_fallback_safe_default",
            tool_trace=traces,
            player_text_used=player_text,
        )

    @staticmethod
    def _safe_phase(value: str) -> str:
        phase = value.lower().strip()
        if phase in {"text", "end"}:
            return phase
        return "text"

    @staticmethod
    def _address_player(user_name: str, hr_reply: str) -> str:
        name = (user_name or "").strip()
        reply = (hr_reply or "").strip()
        if not reply:
            return reply
        if not name:
            return reply
        if name in reply:
            return reply
        return f"{name}，{reply}"
