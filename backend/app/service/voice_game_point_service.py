from __future__ import annotations

from dataclasses import dataclass

from app.shared_types.game_types import GamePointHint, SessionState, TurnDelta


@dataclass(frozen=True)
class GamePointRule:
    point_id: str
    trap_type: str
    explanation: str
    hr_keywords: tuple[str, ...]
    player_keywords: tuple[str, ...]
    player_all_keywords: tuple[str, ...] = ()


VOICE_GAME_POINTS: tuple[GamePointRule, ...] = (
    GamePointRule(
        point_id="gp_salary_anchor",
        trap_type="谁先报价",
        explanation="别急着先报数字，优先把预算区间和薪资结构问回来。",
        hr_keywords=("期望薪资", "预期是多少", "你先说", "先报", "预算来协商"),
        player_keywords=("预算", "区间", "薪资结构", "定位"),
        player_all_keywords=("先",),
    ),
    GamePointRule(
        point_id="gp_equity_bundle",
        trap_type="期权画饼",
        explanation="把现金和期权拆开谈，别让 HR 用未来想象替代当下现金。",
        hr_keywords=("期权", "总包", "未来价值", "现金只是一部分"),
        player_keywords=("分开谈", "现金", "基本保障", "替代"),
    ),
    GamePointRule(
        point_id="gp_overtime_blur",
        trap_type="加班费模糊",
        explanation="追问加班费计算方式，最好要求写进合同。",
        hr_keywords=("弹性工作", "14薪已经包含", "不单独讲", "加班考虑进去了"),
        player_keywords=("劳动法", "加班费", "写进合同", "计算方式"),
    ),
    GamePointRule(
        point_id="gp_social_security",
        trap_type="社保基数模糊",
        explanation="继续追问缴纳基数和公积金比例，最好让 HR 给到明确数字。",
        hr_keywords=("按标准", "正常缴纳", "该有的都有", "五险一金正常"),
        player_keywords=("基数", "实际工资", "公积金比例", "写明"),
    ),
    GamePointRule(
        point_id="gp_probation_promise",
        trap_type="试用期画饼",
        explanation="口头承诺不够，要求把调薪标准或试用期时长写实。",
        hr_keywords=("转正后", "根据表现", "行业惯例", "review薪资", "试用期"),
        player_keywords=("写入合同", "考核标准", "调薪标准", "缩短试用期"),
    ),
)


def initial_game_point_id(scene_id: str) -> str | None:
    return VOICE_GAME_POINTS[0].point_id if scene_id == "scene_001" else None


def build_voice_round_guidance(session_state: SessionState) -> str:
    if session_state.interaction_mode != "voice":
        return ""

    parts: list[str] = []
    active_rule = _rule_by_point_id(session_state.active_game_point_id) or _rule_for_round(session_state)
    if active_rule:
        parts.append(
            f"当前优先自然抛出博弈点「{active_rule.trap_type}」。"
            f"话术方向可围绕：{active_rule.explanation}"
            "不要把规则讲穿，要像真人 HR 在通话里施压。"
        )

    if session_state.hr_patience <= 18:
        parts.append("HR 耐心已经很低，回复里要直接表达流程快失去推进空间，并质疑候选人的诚意。")
    elif session_state.hr_patience <= 35:
        parts.append("HR 耐心在下降，回复里要明确带出“我这边耐心有限”或“再这样很难推进”的暗示。")
    return " ".join(parts)


def infer_game_point_hint(
    session_state: SessionState,
    *,
    hr_reply: str,
    player_text: str,
    delta: TurnDelta,
) -> GamePointHint | None:
    hr_text = (hr_reply or "").strip()
    player = (player_text or "").strip()
    active_rule = _rule_by_point_id(session_state.active_game_point_id)

    if active_rule and _player_resolved(active_rule, player):
        return GamePointHint(
            point_id=active_rule.point_id,
            trap_type=active_rule.trap_type,
            explanation=_resolved_explanation(active_rule, delta),
            status="resolved",
        )

    for rule in VOICE_GAME_POINTS:
        if rule.point_id in session_state.resolved_game_points:
            continue
        if _hr_triggered(rule, hr_text):
            return GamePointHint(
                point_id=rule.point_id,
                trap_type=rule.trap_type,
                explanation=rule.explanation,
                status="active",
            )

    if session_state.hr_patience + delta.hr_patience <= 18:
        return GamePointHint(
            point_id="gp_low_patience",
            trap_type="诚意告急",
            explanation="HR 耐心很低了，下一句要更聚焦关键诉求，不然可能直接收不到 offer。",
            status="active",
        )
    return None


def apply_game_point_effects(session_state: SessionState, *, player_text: str, delta: TurnDelta) -> TurnDelta:
    if session_state.interaction_mode != "voice":
        return delta

    active_rule = _rule_by_point_id(session_state.active_game_point_id)
    if not active_rule or not _player_resolved(active_rule, player_text):
        return delta

    buffed = delta.model_copy(deep=True)
    buffed.trap_count = max(1, buffed.trap_count)

    if active_rule.point_id == "gp_salary_anchor":
        buffed.info_exposure = max(-12, buffed.info_exposure - 6)
        buffed.salary_offer = min(5000, buffed.salary_offer + 1000)
    elif active_rule.point_id == "gp_equity_bundle":
        buffed.info_exposure = max(-12, buffed.info_exposure - 4)
        buffed.salary_offer = min(5000, buffed.salary_offer + 1500)
    elif active_rule.point_id == "gp_overtime_blur":
        buffed.hr_patience = max(-15, buffed.hr_patience - 4)
        buffed.law_citation_count = min(1, buffed.law_citation_count + (1 if "劳动法" in player_text else 0))
    elif active_rule.point_id == "gp_social_security":
        buffed.hr_patience = max(-15, buffed.hr_patience - 3)
        buffed.info_exposure = max(-12, buffed.info_exposure - 4)
    elif active_rule.point_id == "gp_probation_promise":
        buffed.hr_patience = max(-15, buffed.hr_patience - 4)
        buffed.info_exposure = max(-12, buffed.info_exposure - 3)
    return buffed


def sync_game_point_state(session_state: SessionState, hint: GamePointHint | None) -> None:
    if session_state.interaction_mode != "voice" or hint is None:
        return

    if hint.status == "resolved":
        if hint.point_id not in session_state.resolved_game_points:
            session_state.resolved_game_points.append(hint.point_id)
        session_state.active_game_point_id = _next_unresolved_point_id(session_state)
        return

    if hint.point_id.startswith("gp_") and hint.point_id != "gp_low_patience":
        session_state.active_game_point_id = hint.point_id


def _rule_by_point_id(point_id: str | None) -> GamePointRule | None:
    if not point_id:
        return None
    for rule in VOICE_GAME_POINTS:
        if rule.point_id == point_id:
            return rule
    return None


def _rule_for_round(session_state: SessionState) -> GamePointRule | None:
    unresolved = [rule for rule in VOICE_GAME_POINTS if rule.point_id not in session_state.resolved_game_points]
    if not unresolved:
        return None
    index = min(max(session_state.round_index - 1, 0) // 2, len(unresolved) - 1)
    return unresolved[index]


def _next_unresolved_point_id(session_state: SessionState) -> str | None:
    for rule in VOICE_GAME_POINTS:
        if rule.point_id not in session_state.resolved_game_points:
            return rule.point_id
    return None


def _hr_triggered(rule: GamePointRule, hr_text: str) -> bool:
    return any(keyword in hr_text for keyword in rule.hr_keywords)


def _player_resolved(rule: GamePointRule, player_text: str) -> bool:
    if not player_text:
        return False
    if rule.player_all_keywords and not all(keyword in player_text for keyword in rule.player_all_keywords):
        return False
    return sum(1 for keyword in rule.player_keywords if keyword in player_text) >= 2


def _resolved_explanation(rule: GamePointRule, delta: TurnDelta) -> str:
    if rule.point_id == "gp_salary_anchor":
        return "你把预算问题抛回给 HR 了，继续逼对方给区间和结构。"
    if rule.point_id == "gp_equity_bundle":
        if delta.salary_offer > 0:
            return f"你拆开了现金和期权，现金已开始松动，当前薪资 +{delta.salary_offer // 1000}K。"
        return "你成功拆开了现金和期权，继续盯住现金别被带偏。"
    if rule.point_id == "gp_overtime_blur":
        return "你抓住了加班费条款，下一步要继续要求写进合同。"
    if rule.point_id == "gp_social_security":
        return "你把社保问题问到具体层面了，继续追数字和合同写明。"
    if rule.point_id == "gp_probation_promise":
        return "你没有接口头画饼，下一步盯住书面条款或试用期时长。"
    return "这轮你识破了 HR 的博弈点，继续把关键条件谈实。"
