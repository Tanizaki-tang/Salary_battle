from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]
from langchain_openai import ChatOpenAI  # pyright: ignore[reportMissingImports]

from app.modules.agent.tools.voice_battle_tool import VoiceBattleTool
from app.prompt.character_prompt import build_system_prompt
from app.service.llm_service import load_config_from_env
from app.shared_types.game_types import AgentToolCallTrace, AgentTurnDecision, SessionState, TurnDelta, VoiceTurnPayload

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompt"
DEFAULT_PROMPT_FILE = "default_system_prompt.txt"


class HrNegotiationAgent:
    def __init__(self, voice_tool: VoiceBattleTool) -> None:
        self._voice_tool = voice_tool
        self._llm: ChatOpenAI | None = None

    def decide_text_turn(self, session_state: SessionState, player_text: str) -> AgentTurnDecision:
        text = (player_text or "").strip()
        if not text:
            text = "我希望了解这份 offer 的组成和边界。"
        return self._decide(session_state=session_state, player_text=text, traces=[])

    def decide_voice_turn(self, session_state: SessionState, voice_payload: VoiceTurnPayload) -> AgentTurnDecision:
        transcript, _confidence, trace = self._voice_tool.transcribe_for_agent(voice_payload)
        text = transcript or "我想确认语音里提到的薪资与福利细则。"
        return self._decide(session_state=session_state, player_text=text, traces=[trace])

    def _decide(self, *, session_state: SessionState, player_text: str, traces: list[AgentToolCallTrace]) -> AgentTurnDecision:
        base_result = self._base_turn_result(session_state)
        try:
            llm = self._invoke_langchain_llm(
                scene_context=session_state.scene_context.model_dump(),
                session_state=session_state.model_dump(),
                player_text=player_text,
                base_turn_result=base_result,
            )
        except Exception:
            return self._safe_default_decision(session_state=session_state, player_text=player_text, traces=traces)

        return AgentTurnDecision(
            hr_reply=self._address_player(session_state.user_name, str(llm.get("hr_reply", base_result["hr_reply"])) or base_result["hr_reply"]),
            inferred_strategy=str(llm.get("inferred_strategy", "probe")),
            delta=TurnDelta(
                hr_patience=int(llm.get("delta_hr_patience", 0)),
                info_exposure=int(llm.get("delta_info_exposure", 0)),
                trap_count=int(llm.get("delta_trap_count", 0)),
                salary_offer=int(llm.get("delta_salary_offer", 0)),
                equity_ratio=float(llm.get("delta_equity_ratio", 0.0)),
                law_citation_count=int(llm.get("delta_law_citation_count", 0)),
                misjudge_count=int(llm.get("delta_misjudge_count", 0)),
            ),
            trap_id=llm.get("trap_id"),
            next_phase_hint=self._safe_phase(str(llm.get("next_phase_hint", "text"))),
            should_end=bool(llm.get("should_end", False)),
            reason=str(llm.get("reason", "agent_decision")),
            tool_trace=traces,
            player_text_used=player_text,
        )

    def _invoke_langchain_llm(
        self,
        *,
        scene_context: dict[str, Any],
        session_state: dict[str, Any],
        player_text: str,
        base_turn_result: dict[str, Any],
    ) -> dict[str, Any]:
        scene_id = str(scene_context.get("meta", {}).get("scene_id", "scene_001"))
        system_prompt = self._load_scene_prompt(scene_id)
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
        llm = self._get_llm()
        response = llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=json.dumps(user_payload, ensure_ascii=False)),
            ]
        )
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

    def _load_scene_prompt(self, scene_id: str) -> str:
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

    def _get_llm(self) -> ChatOpenAI:
        if self._llm is None:
            cfg = load_config_from_env()
            self._llm = ChatOpenAI(
                api_key=cfg.api_key,
                base_url=cfg.base_url,
                model=cfg.model,
                temperature=0.2,
                timeout=cfg.timeout,
            )
        return self._llm

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
