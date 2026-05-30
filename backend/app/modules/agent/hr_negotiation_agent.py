from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable

from langchain_core.messages import HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]
from langchain_openai import ChatOpenAI  # pyright: ignore[reportMissingImports]
from openai import NotFoundError  # pyright: ignore[reportMissingImports]

from app.modules.agent.tools.voice_battle_tool import VoiceBattleTool
from app.prompt.character_prompt import build_system_prompt
from app.service.history_service import (
    build_agent_reply_payload,
    build_agent_state_payload,
    build_agent_turn_payload,
)
from app.service.llm_service import DEFAULT_MODEL, LLMConfig, load_config_from_env
from app.shared_types.game_types import AgentToolCallTrace, AgentTurnDecision, SessionState, TurnDelta, VoiceTurnPayload

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompt"
DEFAULT_PROMPT_FILE = "default_system_prompt.txt"
logger = logging.getLogger(__name__)

REPLY_STREAM_BASE_PROMPT = (
    "你是 HR 谈判官，正在与候选人进行 offer 谈判。\n"
    "根据场景规则与人格设定，用口语化中文直接回复候选人。\n"
    "要求：只输出你要说的话；不要 JSON；不要 markdown；不要解释或分析；2-4 句为宜。"
)

STATE_DELTA_BASE_PROMPT = (
    "你是谈判游戏状态评估器。HR 口语回复已经生成，你的任务是根据玩家输入、"
    "HR 回复与当前谈判状态，输出状态修正 JSON。\n"
    "只返回 JSON，不要额外文本。\n"
    "必须先判断玩家意图分类，再给出状态增量。\n"
    "数值约束: delta_hr_patience[-15,10], delta_info_exposure[-12,18], delta_trap_count[0,1], "
    "delta_salary_offer[0,5000], delta_equity_ratio[0,0.2], delta_law_citation_count[0,1], "
    "delta_misjudge_count[0,1]。"
)


class HrNegotiationAgent:
    def __init__(self, voice_tool: VoiceBattleTool) -> None:
        self._voice_tool = voice_tool
        self._llm: ChatOpenAI | None = None
        self._reply_llm: ChatOpenAI | None = None
        self._state_llm: ChatOpenAI | None = None
        self._llm_config: LLMConfig | None = None
        self._active_model: str | None = None

    def decide_text_turn(self, session_state: SessionState, player_text: str) -> AgentTurnDecision:
        text = (player_text or "").strip()
        if not text:
            text = "我希望了解这份 offer 的组成和边界。"
        return self._decide(session_state=session_state, player_text=text, traces=[])

    def decide_voice_turn(self, session_state: SessionState, voice_payload: VoiceTurnPayload) -> AgentTurnDecision:
        transcript, _confidence, trace = self._voice_tool.transcribe_for_agent(voice_payload)
        text = transcript or "我想确认语音里提到的薪资与福利细则。"
        return self._decide(session_state=session_state, player_text=text, traces=[trace])

    def decide_text_turn_stream(
        self, session_state: SessionState, player_text: str, on_delta: Callable[[str], None] | None = None
    ) -> AgentTurnDecision:
        text = (player_text or "").strip()
        if not text:
            text = "我希望了解这份 offer 的组成和边界。"
        return self._decide_stream(session_state=session_state, player_text=text, traces=[], on_delta=on_delta)

    def decide_voice_text_stream(
        self, session_state: SessionState, transcript_text: str, on_delta: Callable[[str], None] | None = None
    ) -> AgentTurnDecision:
        text = (transcript_text or "").strip() or "我想确认语音里提到的薪资与福利细则。"
        return self._decide_stream(session_state=session_state, player_text=text, traces=[], on_delta=on_delta)

    def _decide_stream(
        self,
        *,
        session_state: SessionState,
        player_text: str,
        traces: list[AgentToolCallTrace],
        on_delta: Callable[[str], None] | None,
    ) -> AgentTurnDecision:
        base_result = self._base_turn_result(session_state)
        call_started = time.perf_counter()
        logger.info(
            "LLM_STREAM_START session_id=%s scene_id=%s round=%s text_len=%s",
            session_state.session_id,
            session_state.scene_id,
            session_state.round_index,
            len(player_text),
        )
        try:
            hr_reply_raw = self._stream_hr_reply(
                session_state=session_state,
                player_text=player_text,
                base_turn_result=base_result,
                on_delta=on_delta,
            )
            reply_ms = int((time.perf_counter() - call_started) * 1000)
            state_started = time.perf_counter()
            meta = self._invoke_state_delta(
                session_state=session_state,
                player_text=player_text,
                hr_reply=hr_reply_raw,
                base_turn_result=base_result,
            )
            state_ms = int((time.perf_counter() - state_started) * 1000)
            elapsed_ms = int((time.perf_counter() - call_started) * 1000)
            logger.info(
                "LLM_STREAM_OK session_id=%s round=%s reply_ms=%s state_ms=%s total_ms=%s",
                session_state.session_id,
                session_state.round_index,
                reply_ms,
                state_ms,
                elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - call_started) * 1000)
            logger.exception(
                "LLM_STREAM_FAILED session_id=%s round=%s elapsed_ms=%s error=%s",
                session_state.session_id,
                session_state.round_index,
                elapsed_ms,
                type(exc).__name__,
            )
            return self._safe_default_decision(session_state=session_state, player_text=player_text, traces=traces)

        hr_reply = self._address_player(session_state.user_name, hr_reply_raw or str(base_result["hr_reply"]))
        return AgentTurnDecision(
            hr_reply=hr_reply,
            inferred_strategy=str(meta.get("inferred_strategy", "probe")),
            delta=TurnDelta(
                hr_patience=self._clamp_int(meta.get("delta_hr_patience", 0), -15, 10),
                info_exposure=self._clamp_int(meta.get("delta_info_exposure", 0), -12, 18),
                trap_count=self._clamp_int(meta.get("delta_trap_count", 0), 0, 1),
                salary_offer=self._clamp_int(meta.get("delta_salary_offer", 0), 0, 5000),
                equity_ratio=self._clamp_float(meta.get("delta_equity_ratio", 0.0), 0.0, 0.2),
                law_citation_count=self._clamp_int(meta.get("delta_law_citation_count", 0), 0, 1),
                misjudge_count=self._clamp_int(meta.get("delta_misjudge_count", 0), 0, 1),
            ),
            trap_id=self._safe_trap_id(meta.get("trap_id")),
            next_phase_hint=self._safe_phase(str(meta.get("next_phase_hint", "text"))),
            should_end=bool(meta.get("should_end", False)),
            reason=str(meta.get("reason", "agent_stream_decision")),
            tool_trace=traces,
            player_text_used=player_text,
        )

    def _stream_hr_reply(
        self,
        *,
        session_state: SessionState,
        player_text: str,
        base_turn_result: dict[str, Any],
        on_delta: Callable[[str], None] | None,
    ) -> str:
        system_prompt = self._load_reply_prompt(session_state.scene_id, session_state.hr_personality_id)
        user_payload = build_agent_reply_payload(session_state, player_text)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(user_payload, ensure_ascii=False)),
        ]
        llm = self._get_reply_llm()
        parts: list[str] = []
        for chunk in self._stream_with_fallback(llm, messages):
            piece = self._chunk_text(chunk)
            if not piece:
                continue
            parts.append(piece)
            if on_delta is not None:
                on_delta(piece)
        reply = "".join(parts).strip()
        if reply:
            return reply
        return str(base_turn_result.get("hr_reply", "")).strip()

    def _invoke_state_delta(
        self,
        *,
        session_state: SessionState,
        player_text: str,
        hr_reply: str,
        base_turn_result: dict[str, Any],
    ) -> dict[str, Any]:
        system_prompt = self._load_state_prompt(session_state.scene_id, session_state.hr_personality_id)
        user_payload = build_agent_state_payload(
            session_state,
            player_text,
            hr_reply,
            base_turn_result=base_turn_result,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(user_payload, ensure_ascii=False)),
        ]
        llm = self._get_state_llm()
        try:
            response = llm.invoke(messages)
        except NotFoundError as exc:
            if not self._is_model_not_found(exc) or self._active_model == DEFAULT_MODEL:
                raise
            logger.warning(
                "LLM_MODEL_FALLBACK from=%s to=%s reason=model_not_found",
                self._active_model,
                DEFAULT_MODEL,
            )
            llm = self._build_llm(model=DEFAULT_MODEL, temperature=0.1)
            self._state_llm = llm
            self._active_model = DEFAULT_MODEL
            response = llm.invoke(messages)
        content = response.content if isinstance(response.content, str) else str(response.content)
        parsed = self._parse_json_content(content)
        return {
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

    def _stream_with_fallback(self, llm: ChatOpenAI, messages: list[Any]):
        try:
            yield from llm.stream(messages)
        except NotFoundError as exc:
            if not self._is_model_not_found(exc) or self._active_model == DEFAULT_MODEL:
                raise
            logger.warning(
                "LLM_STREAM_MODEL_FALLBACK from=%s to=%s reason=model_not_found",
                self._active_model,
                DEFAULT_MODEL,
            )
            llm = self._build_llm(model=DEFAULT_MODEL, temperature=self._reply_temperature())
            self._reply_llm = llm
            self._active_model = DEFAULT_MODEL
            yield from llm.stream(messages)

    @staticmethod
    def _chunk_text(chunk: Any) -> str:
        content = getattr(chunk, "content", chunk)
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return str(content)

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
        hr_reply_raw = str(llm.get("hr_reply", base_result["hr_reply"])) or str(base_result["hr_reply"])
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
        system_prompt = self._load_scene_prompt(session_state.scene_id, session_state.hr_personality_id)
        user_payload = build_agent_turn_payload(
            session_state=session_state,
            player_text=player_text,
            base_turn_result=base_turn_result,
        )
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(user_payload, ensure_ascii=False)),
        ]
        llm = self._get_llm()
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
        content = response.content if isinstance(response.content, str) else str(response.content)
        parsed = self._parse_json_content(content)
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

    def _load_scene_prompt(self, scene_id: str, personality_id: str | None = None) -> str:
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
        return build_system_prompt(base_prompt=base_prompt, scene_id=scene_id, personality_id=personality_id)

    def _load_reply_prompt(self, scene_id: str, personality_id: str | None = None) -> str:
        return build_system_prompt(
            base_prompt=REPLY_STREAM_BASE_PROMPT,
            scene_id=scene_id,
            personality_id=personality_id,
        )

    def _load_state_prompt(self, scene_id: str, personality_id: str | None = None) -> str:
        return build_system_prompt(
            base_prompt=STATE_DELTA_BASE_PROMPT,
            scene_id=scene_id,
            personality_id=personality_id,
        )

    @staticmethod
    def _reply_temperature() -> float:
        raw = os.getenv("BAILIAN_REPLY_TEMPERATURE", "0.7").strip()
        try:
            return float(raw)
        except ValueError:
            return 0.7

    def _get_llm(self) -> ChatOpenAI:
        if self._llm is None:
            self._llm_config = load_config_from_env()
            self._active_model = self._llm_config.model
            self._llm = self._build_llm(model=self._active_model, temperature=0.1)
        return self._llm

    def _get_reply_llm(self) -> ChatOpenAI:
        if self._reply_llm is None:
            self._llm_config = load_config_from_env()
            self._active_model = self._llm_config.model
            self._reply_llm = self._build_llm(model=self._active_model, temperature=self._reply_temperature())
        return self._reply_llm

    def _get_state_llm(self) -> ChatOpenAI:
        if self._state_llm is None:
            self._llm_config = load_config_from_env()
            self._active_model = self._llm_config.model
            self._state_llm = self._build_llm(model=self._active_model, temperature=0.1)
        return self._state_llm

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
        if phase in {"text", "voice", "end"}:
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
