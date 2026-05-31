from __future__ import annotations

import json
import logging
import random
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage  # pyright: ignore[reportMissingImports]
from langchain_openai import ChatOpenAI  # pyright: ignore[reportMissingImports]
from openai import BadRequestError, NotFoundError  # pyright: ignore[reportMissingImports]

from app.modules.card_game.card_dialogue_constants import ALL_STRATEGIES, OPTION_FALLBACK, STRATEGY_SPECS
from app.modules.card_game.card_engine import apply_delta, compute_delta, pick_hr_reply, pick_question
from app.prompt.dialogue_style import (
    DIALOGUE_LENGTH_RULES,
    HR_QUESTION_FIELD_HINT,
    HR_REPLY_FIELD_HINT,
    PLAYER_REPLY_FIELD_HINT,
    clamp_hr_question,
    clamp_hr_reply,
    clamp_player_reply,
)
from app.prompt.hr_personality import get_personality_meta
from app.service.llm_service import (
    DEFAULT_MODEL,
    LLMConfig,
    get_card_game_dialogue_mode,
    load_config_from_env,
    qwen_disable_thinking_extra,
)
from app.shared_types.card_game_types import CardGameState, CardStrategyId

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_FULL = f"""你是谈薪卡牌博弈剧本生成器。只输出 JSON，无 markdown。
{DIALOGUE_LENGTH_RULES}
每轮只给玩家 3 张策略牌：available_strategies 长度必须为 3；并且必须包含 best_strategy_hint。recommended_strategy 必须等于 best_strategy_hint。"""

SYSTEM_PROMPT_LITE = f"""你是谈薪卡牌 HR。只输出 JSON，无 markdown。
{DIALOGUE_LENGTH_RULES}"""


class CardDialogueAgent:
    def __init__(self) -> None:
        self._llm: ChatOpenAI | None = None
        self._llm_config: LLMConfig | None = None
        self._active_model: str | None = None
        self._mode = get_card_game_dialogue_mode()

    def generate_round_opening(
        self, state: CardGameState
    ) -> tuple[str, list[CardStrategyId], dict[str, str], CardStrategyId]:
        if self._mode == "off":
            return self._fallback_opening(state)
        if self._mode == "lite":
            return self._generate_opening_lite(state)
        return self._generate_opening_full(state)

    def generate_turn_dialogue(
        self,
        state: CardGameState,
        strategy: CardStrategyId,
        player_text: str,
        *,
        prepare_next_round: bool,
        next_round_index: int,
    ) -> tuple[str, str, list[CardStrategyId], dict[str, str], CardStrategyId]:
        if self._mode == "off":
            return self._fallback_turn(strategy, state, prepare_next_round, next_round_index)
        if self._mode == "lite":
            return self._generate_turn_lite(state, strategy, player_text, prepare_next_round, next_round_index)
        return self._generate_turn_full(state, strategy, player_text, prepare_next_round, next_round_index)

    def _generate_opening_lite(
        self, state: CardGameState
    ) -> tuple[str, list[CardStrategyId], dict[str, str], CardStrategyId]:
        try:
            best = self._pick_best_strategy(state)
            payload = self._invoke(
                {
                    "task": "hr_question",
                    "round_index": state.round_index,
                    "user_name": state.user_name,
                    "hr_personality": self._personality_block(state.hr_personality_id),
                    "stats": state.stats.model_dump(),
                    "best_strategy_hint": best,
                    "output_schema": {"hr_question": HR_QUESTION_FIELD_HINT},
                },
                system_prompt=SYSTEM_PROMPT_LITE,
                max_tokens=120,
            )
            question = clamp_hr_question(str(payload.get("hr_question", "")).strip())
            if not question:
                raise ValueError("empty hr_question")
            available, options = self._fallback_pack(best)
            return question, available, options, best
        except Exception as exc:
            logger.warning("CARD_LLM_OPENING_LITE_FALLBACK session=%s err=%s", state.session_id, exc)
            return self._fallback_opening(state)

    def _generate_opening_full(
        self, state: CardGameState
    ) -> tuple[str, list[CardStrategyId], dict[str, str], CardStrategyId]:
        try:
            best = self._pick_best_strategy(state)
            payload = self._invoke(
                {
                    "task": "round_opening",
                    "round_index": state.round_index,
                    "max_round": state.max_round,
                    "user_name": state.user_name,
                    "hr_personality": self._personality_block(state.hr_personality_id),
                    "stats": state.stats.model_dump(),
                    "strategy_specs": STRATEGY_SPECS,
                    "best_strategy_hint": best,
                    "output_schema": {
                        "hr_question": HR_QUESTION_FIELD_HINT,
                        "available_strategies": "长度为3的策略数组；只能从 strategy_specs 的 key 里选；必须包含 best_strategy_hint。",
                        "recommended_strategy": "必须等于 best_strategy_hint。",
                        "option_replies": f"仅对 available_strategies 内的策略给玩家回复文案，每条{PLAYER_REPLY_FIELD_HINT}",
                    },
                },
                system_prompt=SYSTEM_PROMPT_FULL,
                max_tokens=650,
            )
            question = clamp_hr_question(str(payload.get("hr_question", "")).strip())
            available, options = self._normalize_pack(payload, best)
            if not question:
                raise ValueError("empty hr_question")
            return question, available, options, best
        except Exception as exc:
            logger.warning("CARD_LLM_ROUND_OPENING_FALLBACK session=%s err=%s", state.session_id, exc)
            return self._fallback_opening(state)

    def _generate_turn_lite(
        self,
        state: CardGameState,
        strategy: CardStrategyId,
        player_text: str,
        prepare_next_round: bool,
        next_round_index: int,
    ) -> tuple[str, str, list[CardStrategyId], dict[str, str], CardStrategyId]:
        try:
            system = SYSTEM_PROMPT_LITE
            payload = self._invoke(
                {
                    "task": "hr_reply",
                    "round_index": state.round_index,
                    "user_name": state.user_name,
                    "hr_personality": self._personality_block(state.hr_personality_id),
                    "stats": state.stats.model_dump(),
                    "current_hr_question": state.current_question,
                    "player_strategy": strategy,
                    "player_text": player_text,
                    "output_schema": {"hr_reply": HR_REPLY_FIELD_HINT},
                },
                system_prompt=system,
                max_tokens=140,
            )
            hr_reply = clamp_hr_reply(str(payload.get("hr_reply", "")).strip())
            if not hr_reply:
                raise ValueError("empty hr_reply")
            if not prepare_next_round:
                return hr_reply, "", [], {}, strategy
            next_q, available, options, best = self._generate_opening_lite(
                state.model_copy(update={"round_index": next_round_index})
            )
            return hr_reply, next_q, available, options, best
        except Exception as exc:
            logger.warning("CARD_LLM_TURN_LITE_FALLBACK session=%s strategy=%s err=%s", state.session_id, strategy, exc)
            return self._fallback_turn(strategy, state, prepare_next_round, next_round_index)

    def _generate_turn_full(
        self,
        state: CardGameState,
        strategy: CardStrategyId,
        player_text: str,
        prepare_next_round: bool,
        next_round_index: int,
    ) -> tuple[str, str, list[CardStrategyId], dict[str, str], CardStrategyId]:
        try:
            system = SYSTEM_PROMPT_FULL
            next_state = state.model_copy(update={"round_index": next_round_index}) if prepare_next_round else state
            best = self._pick_best_strategy(next_state) if prepare_next_round else strategy
            payload = self._invoke(
                {
                    "task": "turn_resolution",
                    "round_index": state.round_index,
                    "next_round_index": next_round_index if prepare_next_round else None,
                    "user_name": state.user_name,
                    "hr_personality": self._personality_block(state.hr_personality_id),
                    "stats_after_delta_hint": state.stats.model_dump(),
                    "current_hr_question": state.current_question,
                    "player_strategy": strategy,
                    "player_text": player_text,
                    "strategy_spec": STRATEGY_SPECS[strategy],
                    "prepare_next_round": prepare_next_round,
                    "strategy_specs": STRATEGY_SPECS if prepare_next_round else None,
                    "best_strategy_hint": best if prepare_next_round else None,
                    "output_schema": {
                        "hr_reply": HR_REPLY_FIELD_HINT,
                        "next_hr_question": HR_QUESTION_FIELD_HINT,
                        "available_strategies": "长度为3的策略数组；只能从 strategy_specs 的 key 里选；必须包含 best_strategy_hint。",
                        "recommended_strategy": "必须等于 best_strategy_hint。",
                        "option_replies": f"仅对 available_strategies 内的策略给玩家回复文案，每条{PLAYER_REPLY_FIELD_HINT}",
                    },
                },
                system_prompt=system,
                max_tokens=650,
            )
            hr_reply = clamp_hr_reply(str(payload.get("hr_reply", "")).strip())
            if not hr_reply:
                raise ValueError("empty hr_reply")
            if not prepare_next_round:
                return hr_reply, "", [], {}, strategy
            next_q = clamp_hr_question(str(payload.get("next_hr_question", "")).strip())
            available, options = self._normalize_pack(payload, best)
            if not next_q:
                raise ValueError("empty next_hr_question")
            return hr_reply, next_q, available, options, best
        except Exception as exc:
            logger.warning("CARD_LLM_TURN_FALLBACK session=%s strategy=%s err=%s", state.session_id, strategy, exc)
            return self._fallback_turn(strategy, state, prepare_next_round, next_round_index)

    def _fallback_turn(
        self,
        strategy: CardStrategyId,
        state: CardGameState,
        prepare_next_round: bool,
        next_round_index: int,
    ) -> tuple[str, str, list[CardStrategyId], dict[str, str], CardStrategyId]:
        hr_reply = pick_hr_reply(strategy)
        if not prepare_next_round:
            return hr_reply, "", [], {}, strategy
        next_q = pick_question(next_round_index, state.user_name)
        next_state = state.model_copy(update={"round_index": next_round_index})
        best = self._pick_best_strategy(next_state)
        available, options = self._fallback_pack(best)
        return hr_reply, next_q, available, options, best

    def _fallback_opening(
        self, state: CardGameState
    ) -> tuple[str, list[CardStrategyId], dict[str, str], CardStrategyId]:
        question = pick_question(state.round_index, state.user_name)
        best = self._pick_best_strategy(state)
        available, options = self._fallback_pack(best)
        return question, available, options, best

    @staticmethod
    def _fallback_options(user_name: str, question: str) -> dict[str, str]:
        del user_name, question
        return dict(OPTION_FALLBACK)

    @staticmethod
    def _personality_block(personality_id: str) -> dict[str, str]:
        meta = get_personality_meta(personality_id)
        return {
            "personality_id": meta.personality_id,
            "name": meta.name,
            "tagline": meta.tagline,
        }

    @staticmethod
    def _normalize_pack(payload: dict[str, Any], best: CardStrategyId) -> tuple[list[CardStrategyId], dict[str, str]]:
        raw_list = payload.get("available_strategies")
        available = CardDialogueAgent._normalize_strategy_list(raw_list, best)
        raw_options = payload.get("option_replies")
        if not isinstance(raw_options, dict):
            raw_options = {}
        options: dict[str, str] = {}
        for key in available:
            text = clamp_player_reply(str(raw_options.get(key, "")).strip())
            if not text:
                text = OPTION_FALLBACK[key]
            options[key] = text
        return available, options

    @staticmethod
    def _normalize_strategy_list(raw: Any, best: CardStrategyId) -> list[CardStrategyId]:
        picked: list[CardStrategyId] = []
        if isinstance(raw, list):
            for item in raw:
                s = str(item).strip()
                if s in ALL_STRATEGIES and s not in picked:
                    picked.append(s)  # type: ignore[arg-type]
        if best not in picked:
            picked.insert(0, best)
        pool = [s for s in ALL_STRATEGIES if s not in picked]
        random.shuffle(pool)
        picked.extend(pool)
        return picked[:3]

    @staticmethod
    def _fallback_pack(best: CardStrategyId) -> tuple[list[CardStrategyId], dict[str, str]]:
        available = CardDialogueAgent._normalize_strategy_list([], best)
        options = dict(OPTION_FALLBACK)
        return available, {k: options[k] for k in available}

    @staticmethod
    def _pick_best_strategy(state: CardGameState) -> CardStrategyId:
        best: CardStrategyId = "probe"
        best_score = -1e18
        for s in ALL_STRATEGIES:
            delta = compute_delta(s, state.hr_personality_id, state.round_index, state.strategy_history)
            next_stats = apply_delta(state.stats, delta)
            if next_stats.satisfaction <= 0:
                continue
            score = (
                delta.salary_k * 35.0
                + delta.work_hours * 25.0
                + delta.security * 25.0
                + float(delta.satisfaction) * 15.0
            )
            if next_stats.salary_k >= 18.0:
                score += 50.0
            if next_stats.work_hours >= 7.0:
                score += 50.0
            if next_stats.security >= 3.0:
                score += 50.0
            if score > best_score:
                best_score = score
                best = s  # type: ignore[assignment]
        return best

    def _invoke(
        self,
        payload: dict[str, Any],
        *,
        system_prompt: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        task = str(payload.get("task", "unknown"))
        started = time.perf_counter()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
        llm = self._get_llm(max_tokens=max_tokens)
        try:
            response = llm.invoke(messages)
        except (NotFoundError, BadRequestError) as exc:
            if not self._is_model_not_found(exc) or self._active_model == DEFAULT_MODEL:
                raise
            logger.warning("CARD_LLM_MODEL_FALLBACK to=%s", DEFAULT_MODEL)
            llm = self._build_llm(model=DEFAULT_MODEL, temperature=0.35, max_tokens=max_tokens)
            self._llm = llm
            self._active_model = DEFAULT_MODEL
            response = llm.invoke(messages)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "CARD_LLM_OK task=%s mode=%s model=%s elapsed_ms=%s",
            task,
            self._mode,
            self._active_model,
            elapsed_ms,
        )
        content = response.content if isinstance(response.content, str) else str(response.content)
        parsed = self._parse_json_content(content)
        if not isinstance(parsed, dict):
            raise ValueError("LLM output must be JSON object")
        return parsed

    def _get_llm(self, *, max_tokens: int) -> ChatOpenAI:
        if self._llm_config is None:
            self._llm_config = load_config_from_env()
            self._active_model = self._llm_config.model
        model = self._active_model or self._llm_config.model
        return self._build_llm(model=model, temperature=0.35, max_tokens=max_tokens)

    def _build_llm(self, model: str, *, temperature: float, max_tokens: int) -> ChatOpenAI:
        cfg = self._llm_config or load_config_from_env()
        self._llm_config = cfg
        extra = qwen_disable_thinking_extra(model)
        kwargs: dict[str, Any] = {
            "api_key": cfg.api_key,
            "base_url": cfg.base_url,
            "model": model,
            "timeout": cfg.timeout,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if extra:
            kwargs["model_kwargs"] = {"extra_body": extra}
        return ChatOpenAI(**kwargs)

    @staticmethod
    def _parse_json_content(content: str) -> dict[str, Any]:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:].strip()
        parsed = json.loads(text)
        if not isinstance(parsed, dict):
            raise ValueError("expected JSON object")
        return parsed

    @staticmethod
    def _is_model_not_found(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(kw in msg for kw in [
            "model_not_found",
            "does not exist",
            "model not found",
            "invalid model",
            "unknown model",
        ])
