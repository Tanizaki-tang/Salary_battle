from __future__ import annotations

import math
import random
from dataclasses import dataclass

from app.modules.card_game.card_dialogue_constants import ALL_STRATEGIES, OPTION_FALLBACK
from app.shared_types.card_game_types import (
    CardDeltaView,
    CardGameOutcome,
    CardGameScoreBreakdown,
    CardGameSettleResult,
    CardGameState,
    CardGameStats,
    CardStrategyId,
    CardTurnResult,
)

SALARY_MIN = 8.0
SALARY_MAX = 22.0
SALARY_HIDDEN_MAX = 100.0
SAT_MAX = 10.0
WORK_HOURS_MAX = 10.0
SECURITY_MAX = 5.0

DEAL_THRESHOLDS = {
    "salary_k": 18.0,
    "work_hours": 7.0,
    "security": 3.0,
    "satisfaction": 0.0,
}


@dataclass(frozen=True, slots=True)
class BaseDelta:
    satisfaction: float
    salary_k: float
    work_hours: float
    security: float


BASE_DELTAS: dict[CardStrategyId, BaseDelta] = {
    "strong_push": BaseDelta(-3.0, 2.5, 0.5, 0.3),
    "probe": BaseDelta(-1.0, 0.5, 1.5, 1.0),
    "concede": BaseDelta(1.0, 0.5, -1.0, 0.5),
    "counter_pressure": BaseDelta(-2.0, 2.0, 1.0, 0.5),
    "expose_rhetoric": BaseDelta(-2.0, 1.0, 1.0, 1.5),
    "off_topic": BaseDelta(1.5, 0.0, 0.3, 0.2),
}

# personality_id -> strategy -> (sat, salary, hours, security) multipliers; None = 1.0
PERSONALITY_MODS: dict[str, dict[CardStrategyId, tuple[float, float, float, float]]] = {
    "hr_smiling_tiger": {
        "strong_push": (1.1, 0.9, 1.0, 1.0),
        "probe": (1.2, 1.0, 1.0, 1.0),
        "concede": (1.0, 0.8, 1.0, 1.0),
        "counter_pressure": (1.2, 1.0, 1.0, 1.0),
        "expose_rhetoric": (1.5, 1.2, 1.0, 1.3),
        "off_topic": (0.8, 1.0, 1.0, 1.0),
    },
    "hr_honest": {
        "strong_push": (0.8, 1.3, 1.0, 1.0),
        "probe": (1.0, 1.0, 1.3, 1.5),
        "concede": (1.3, 1.2, 1.0, 1.0),
        "counter_pressure": (0.8, 1.2, 1.0, 1.0),
        "expose_rhetoric": (0.7, 1.0, 1.3, 1.3),
        "off_topic": (1.3, 1.0, 1.0, 1.0),
    },
    "hr_aggressive": {
        "strong_push": (1.5, 0.7, 1.0, 1.0),
        "probe": (1.3, 1.0, 0.7, 1.0),
        "concede": (1.0, 1.0, 1.0, 1.0),
        "counter_pressure": (1.5, 1.0, 1.0, 1.0),
        "expose_rhetoric": (1.3, 1.0, 1.0, 1.0),
        "off_topic": (0.5, 1.0, 1.0, 1.0),
    },
    "hr_robot": {
        "strong_push": (1.0, 1.0, 1.0, 1.0),
        "probe": (1.0, 1.0, 1.0, 1.0),
        "concede": (1.0, 1.0, 1.0, 1.0),
        "counter_pressure": (1.0, 1.0, 1.0, 1.0),
        "expose_rhetoric": (1.0, 1.0, 1.0, 1.0),
        "off_topic": (0.3, 1.0, 1.0, 1.0),
    },
    "hr_newbie": {
        "strong_push": (1.3, 1.5, 1.0, 1.0),
        "probe": (1.0, 1.0, 1.5, 1.5),
        "concede": (1.5, 1.2, 1.0, 1.0),
        "counter_pressure": (1.3, 1.4, 1.0, 1.0),
        "expose_rhetoric": (1.0, 1.0, 1.5, 1.5),
        "off_topic": (1.5, 1.0, 1.0, 1.0),
    },
}

ROUND_QUESTIONS: list[str] = [
    "我们这边 base 15K 是统一标准，你怎么看？",
    "你更在意薪资数字，还是成长空间和团队氛围？",
    "如果绩效浮动比较大，你能接受怎样的区间？",
    "关于加班和弹性，你这边有什么底线吗？",
    "五险一金我们是按合规最低基数，这个你了解吗？",
    "你手上有其他 offer 吗？方便说一下区间吗？",
    "最后几个点我们对齐一下，你最想先谈哪一块？",
    "这是最后一轮了，你现在的整体感受如何？",
]

HR_REPLIES: dict[CardStrategyId, list[str]] = {
    "strong_push": [
        "你这个态度……我先记下了，但预算真的有限。",
        "别这么硬，咱们还是看能不能各退一步。",
    ],
    "probe": [
        "你问得挺细，我把结构给你拆开说明。",
        "这些细节我可以补充，但也要看整体 package。",
    ],
    "concede": [
        "你这个说法我比较能接受，我们再看怎么微调。",
        "嗯，有合作意愿就好办，我帮你争取一下。",
    ],
    "counter_pressure": [
        "你这个问题把我问住了……让我想想怎么回答。",
        "行，你先说说你的优先级，我再对应调整。",
    ],
    "expose_rhetoric": [
        "……好吧，这部分确实需要写清楚。",
        "被你看出来了，我们把它落到纸面上。",
    ],
    "off_topic": [
        "哈哈行，团队氛围确实不错，不过咱们还得聊正事。",
        "闲聊可以，但时间有限，待会还得回到 offer。",
    ],
}


def round_multiplier(round_index: int) -> float:
    if round_index <= 2:
        return 1.0
    if round_index <= 4:
        return 1.3
    if round_index <= 6:
        return 1.6
    return 2.0


def sat_round_multiplier(round_index: int) -> float:
    return round_multiplier(round_index)


def _personality_mod(personality_id: str, strategy: CardStrategyId) -> tuple[float, float, float, float]:
    table = PERSONALITY_MODS.get(personality_id) or PERSONALITY_MODS["hr_robot"]
    return table.get(strategy, (1.0, 1.0, 1.0, 1.0))


def _repeat_penalty(history: list[CardStrategyId], strategy: CardStrategyId) -> float:
    if not history:
        return 1.0
    streak = 0
    for item in reversed(history):
        if item == strategy:
            streak += 1
        else:
            break
    if streak >= 2:
        return 0.5
    if streak >= 1:
        return 0.7
    return 1.0


def _ceil_int(value: float) -> int:
    if value == 0:
        return 0
    return int(math.ceil(value - 1e-9))


def _ceil_tenth(value: float) -> float:
    if value == 0:
        return 0.0
    return math.ceil(value * 10 - 1e-9) / 10.0


def _sat_delta_int(value: float) -> int:
    if value == 0:
        return 0
    return int(math.floor(value + 1e-9))



def compute_delta(
    strategy: CardStrategyId,
    personality_id: str,
    round_index: int,
    history: list[CardStrategyId],
) -> CardDeltaView:
    base = BASE_DELTAS[strategy]
    sat_m, sal_m, wh_m, sec_m = _personality_mod(personality_id, strategy)
    rm = round_multiplier(round_index)
    sat_rm = sat_round_multiplier(round_index)
    repeat = _repeat_penalty(history, strategy)

    raw_sat = base.satisfaction * sat_rm * sat_m
    raw_sal = base.salary_k * rm * sal_m * repeat
    raw_wh = base.work_hours * rm * wh_m * repeat
    raw_sec = base.security * rm * sec_m * repeat

    return CardDeltaView(
        satisfaction=_sat_delta_int(raw_sat),
        salary_k=_ceil_tenth(raw_sal),
        work_hours=_ceil_int(raw_wh),
        security=_ceil_int(raw_sec),
    )


def apply_delta(stats: CardGameStats, delta: CardDeltaView) -> CardGameStats:
    return CardGameStats(
        satisfaction=max(0.0, min(SAT_MAX, stats.satisfaction + delta.satisfaction)),
        salary_k=max(SALARY_MIN, min(SALARY_MAX, stats.salary_k + delta.salary_k)),
        work_hours=max(0.0, min(WORK_HOURS_MAX, stats.work_hours + delta.work_hours)),
        security=max(0.0, min(SECURITY_MAX, stats.security + delta.security)),
    )


def count_conditions(stats: CardGameStats) -> int:
    met = 0
    if stats.salary_k >= DEAL_THRESHOLDS["salary_k"]:
        met += 1
    if stats.work_hours >= DEAL_THRESHOLDS["work_hours"]:
        met += 1
    if stats.security >= DEAL_THRESHOLDS["security"]:
        met += 1
    if stats.satisfaction > DEAL_THRESHOLDS["satisfaction"]:
        met += 1
    return met


def pick_question(round_index: int, user_name: str) -> str:
    idx = min(max(round_index - 1, 0), len(ROUND_QUESTIONS) - 1)
    return f"{user_name}，{ROUND_QUESTIONS[idx]}"


def pick_hr_reply(strategy: CardStrategyId) -> str:
    options = HR_REPLIES.get(strategy, HR_REPLIES["concede"])
    return random.choice(options)


class CardGameEngine:
    def __init__(self, dialogue_agent: object | None = None) -> None:
        self._dialogue = dialogue_agent

    def create_initial_state(
        self,
        session_id: str,
        user_id: str,
        user_name: str,
        hr_personality_id: str,
    ) -> CardGameState:
        state = CardGameState(
            session_id=session_id,
            user_id=user_id,
            user_name=user_name,
            hr_personality_id=hr_personality_id,
        )
        if self._dialogue is not None:
            question, available, options, recommended = self._dialogue.generate_round_opening(state)
        else:
            question = pick_question(1, user_name)
            available = list(ALL_STRATEGIES)[:3]
            options = {k: OPTION_FALLBACK[k] for k in available}
            recommended = available[0]
        return state.model_copy(
            update={
                "current_question": question,
                "available_strategies": available,
                "option_replies": options,
                "recommended_strategy": recommended,
            }
        )

    def play_turn(
        self,
        state: CardGameState,
        strategy: CardStrategyId,
        player_text: str | None = None,
    ) -> tuple[CardGameState, CardTurnResult]:
        if state.status != "ongoing":
            raise ValueError("game already ended")

        if state.available_strategies and strategy not in state.available_strategies:
            raise ValueError("只能从本回合发放的三张牌中选择")

        resolved_player_text = (player_text or "").strip() or (state.option_replies or {}).get(strategy, "").strip()
        if not resolved_player_text:
            resolved_player_text = OPTION_FALLBACK[strategy]

        delta = compute_delta(strategy, state.hr_personality_id, state.round_index, state.strategy_history)
        new_stats = apply_delta(state.stats, delta)
        next_round = state.round_index + 1
        history = [*state.strategy_history, strategy]

        outcome: CardGameOutcome | None = None
        reason = ""
        status = state.status

        if new_stats.satisfaction <= 0:
            outcome = "collapsed"
            reason = "满意度归零，HR 撤回 offer"
            status = "collapsed"
        elif next_round > state.max_round:
            outcome = "forced_deal"
            reason = "第 8 轮结束，强制进入结算"
            status = "forced_settle"

        next_question = ""
        next_options: dict[str, str] = {}
        next_available: list[CardStrategyId] = []
        next_recommended: CardStrategyId | None = None
        if self._dialogue is not None:
            dialogue_state = state.model_copy(update={"stats": new_stats})
            hr_reply, next_question, next_available, next_options, next_recommended = (
                self._dialogue.generate_turn_dialogue(
                dialogue_state,
                strategy,
                resolved_player_text,
                prepare_next_round=status == "ongoing",
                next_round_index=next_round,
            )
            )
        else:
            hr_reply = pick_hr_reply(strategy)
            if status == "ongoing":
                next_question = pick_question(next_round, state.user_name)
                next_available = list(ALL_STRATEGIES)[:3]
                next_options = {k: OPTION_FALLBACK[k] for k in next_available}
                next_recommended = next_available[0]

        next_state = CardGameState(
            session_id=state.session_id,
            user_id=state.user_id,
            user_name=state.user_name,
            hr_personality_id=state.hr_personality_id,
            status=status,
            round_index=next_round if status == "ongoing" else state.round_index,
            max_round=state.max_round,
            stats=new_stats,
            current_question=next_question or state.current_question,
            available_strategies=next_available if status == "ongoing" else [],
            option_replies=next_options if status == "ongoing" else {},
            recommended_strategy=next_recommended if status == "ongoing" else None,
            last_hr_reply=hr_reply,
            last_player_text=resolved_player_text,
            last_strategy=strategy,
            strategy_history=history,
            outcome=outcome,
        )

        result = CardTurnResult(
            hr_reply=hr_reply,
            player_text_used=resolved_player_text,
            next_question=next_question,
            available_strategies=next_available,
            delta=delta,
            stats=new_stats,
            round_index=next_state.round_index,
            is_game_over=status != "ongoing",
            recommended_strategy=next_recommended,
            outcome=outcome,
            outcome_reason=reason,
            option_replies=next_options,
        )
        return next_state, result

    def accept_offer(self, state: CardGameState) -> tuple[CardGameState, CardGameOutcome, str]:
        if state.status != "ongoing":
            raise ValueError("game already ended")
        if state.round_index < 3:
            raise ValueError("第 3 轮后才可接受 offer")

        met = count_conditions(state.stats)
        sat = state.stats.satisfaction
        if sat <= 0:
            outcome: CardGameOutcome = "collapsed"
            reason = "满意度已崩盘，无法接受 offer"
        elif sat <= 1:
            outcome = "low_deal"
            reason = "勉强接受，HR 脸色很难看"
        elif met >= 3:
            outcome = "high_deal"
            reason = "高位成交，多数条件已达成"
        elif met >= 2:
            outcome = "deal"
            reason = "成功成交，部分条件达成"
        else:
            outcome = "deal"
            reason = "条件达成偏少，但仍选择接受"

        next_state = state.model_copy(update={"status": "accepted", "outcome": outcome})
        return next_state, outcome, reason

    def settle(self, state: CardGameState) -> CardGameSettleResult:
        stats = state.stats
        outcome = state.outcome or "forced_deal"

        salary_score = int((stats.salary_k - SALARY_MIN) / (SALARY_MAX - SALARY_MIN) * 100)
        wh_score = int(stats.work_hours * 10)
        sec_score = int(stats.security * 20)
        sat_score = int(stats.satisfaction * 10)

        salary_score = max(0, min(100, salary_score))
        wh_score = max(0, min(100, wh_score))
        sec_score = max(0, min(100, sec_score))
        sat_score = max(0, min(100, sat_score))

        base = salary_score * 0.35 + wh_score * 0.25 + sec_score * 0.25 + sat_score * 0.15
        strategy_count = len(set(state.strategy_history))
        bonus = 5 if strategy_count >= 3 else 0
        penalty = 10 if outcome == "low_deal" else 0
        if outcome == "collapsed":
            final = max(0, int(base * 0.3))
        else:
            final = max(0, min(110, int(round(base + bonus - penalty))))

        grade, medal, title = _grade_for_score(final, outcome)
        tip = _review_tip(outcome, count_conditions(stats), strategy_count)

        return CardGameSettleResult(
            final_score=final,
            grade=grade,
            medal=medal,
            title=title,
            outcome=outcome,
            review_tip=tip,
            conditions_met=count_conditions(stats),
            breakdown=CardGameScoreBreakdown(
                salary=salary_score,
                work_hours=wh_score,
                security=sec_score,
                satisfaction=sat_score,
            ),
            stats=stats,
            strategy_count=strategy_count,
            bonus_diversity=bonus,
            penalty_low_satisfaction=penalty,
        )


def _grade_for_score(score: int, outcome: CardGameOutcome) -> tuple[str, str, str]:
    if outcome == "collapsed":
        return "谈崩了", "💀", "谈判破裂"
    if score >= 95:
        return "谈判大师", "🥇", "谈判大师"
    if score >= 80:
        return "老练求职者", "🥈", "老练求职者"
    if score >= 60:
        return "可造之材", "🥉", "可造之材"
    if score >= 40:
        return "职场小白", "📋", "职场小白"
    return "谈崩了", "💀", "谈崩了"


def _review_tip(outcome: CardGameOutcome, conditions: int, strategies: int) -> str:
    if outcome == "collapsed":
        return "满意度管理失败：进攻牌用太猛，记得穿插温和协商或闲聊救场。"
    if outcome == "high_deal":
        return f"高位成交！达成 {conditions}/4 项条件，策略多样性 {strategies} 种。"
    if outcome == "low_deal":
        return "低满成交：HR 勉强点头，下次可多留满意度缓冲。"
    if outcome == "forced_deal":
        return f"拖满 8 轮强制结算，达成 {conditions}/4 项，可考虑更早接受 offer。"
    return f"成交达成 {conditions}/4 项条件，继续尝试不同策略组合。"
