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


VOICE_GAME_POINTS: dict[str, tuple[GamePointRule, ...]] = {
    "scene_001": (
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
    ),
    "scene_002": (
        GamePointRule(
            point_id="gp_ops_perf_split",
            trap_type="绩效占比膨胀",
            explanation="别只看总包，继续追问基础工资保底数字和绩效保护期。",
            hr_keywords=("绩效好的话", "总包", "3k 绩效", "弹性很大", "去年平均"),
            player_keywords=("基础工资", "保底", "绩效保护", "合同"),
        ),
        GamePointRule(
            point_id="gp_ops_social_base",
            trap_type="五险一金基数陷阱",
            explanation="要求 HR 给出社保基数和公积金比例的具体数字，不要只听体系说法。",
            hr_keywords=("统一体系", "按标准", "绝对合规", "薪酬体系"),
            player_keywords=("基数", "差额", "实际工资", "比例"),
        ),
        GamePointRule(
            point_id="gp_ops_level_anchor",
            trap_type="岗位定级压价",
            explanation="继续挑战职级评定依据，把讨论拉回你的经验和实际贡献。",
            hr_keywords=("P2", "职级", "带宽", "上限就是", "定级"),
            player_keywords=("定级依据", "经验", "项目", "P3"),
        ),
        GamePointRule(
            point_id="gp_ops_quarter_bonus",
            trap_type="季度奖金画饼",
            explanation="不接受平均值和历史数据，继续问奖金公式、KPI 和是否写进合同。",
            hr_keywords=("季度奖", "去年团队平均", "业务情况", "一般都不差"),
            player_keywords=("计算公式", "KPI", "写进合同", "承诺性收入"),
        ),
        GamePointRule(
            point_id="gp_ops_batch_pressure",
            trap_type="批量招聘施压",
            explanation="别被“同批都一样”带偏，直接强调你的项目经历和不可替代性。",
            hr_keywords=("这一批", "统一发 offer", "同批条件", "很多候选人"),
            player_keywords=("独特优势", "项目经验", "结果", "不可替代"),
        ),
    ),
    "scene_003": (
        GamePointRule(
            point_id="gp_trainee_total_package",
            trap_type="总包数字灌水",
            explanation="把总包拆成保底月薪、临时福利和非现金收益，不要被表面数字带偏。",
            hr_keywords=("总包", "房补", "餐补", "培训价值", "25 万"),
            player_keywords=("拆开", "保底月薪", "临时福利", "长期收入"),
        ),
        GamePointRule(
            point_id="gp_trainee_non_compete",
            trap_type="竞业限制轻描淡写",
            explanation="继续追问竞业期限、补偿金和限制范围，这是真实的离职成本。",
            hr_keywords=("行业惯例", "大家都签", "标准条款", "竞业"),
            player_keywords=("竞业限制", "补偿金", "期限", "范围"),
        ),
        GamePointRule(
            point_id="gp_trainee_rotation",
            trap_type="轮岗定岗画饼",
            explanation="不要只听成长空间，继续问定岗标准、薪资下限和考核方式。",
            hr_keywords=("轮岗", "看表现", "公司需求", "空间很大", "定岗"),
            player_keywords=("考核标准", "薪资下限", "P5", "保证"),
        ),
        GamePointRule(
            point_id="gp_trainee_signing",
            trap_type="签字费空间不主动提",
            explanation="如果你有别家报价，就明确问签字费或搬家补贴，不要等 HR 主动说。",
            hr_keywords=("搬家补贴", "一般不提供", "统一标准", "没有 sign-on"),
            player_keywords=("签字费", "sign-on", "竞品", "搬家费"),
        ),
        GamePointRule(
            point_id="gp_trainee_identity",
            trap_type="培训生身份模糊",
            explanation="继续追问合同身份、司龄和培训期离职责任，避免被身份定义反噬。",
            hr_keywords=("培训生", "都一样", "培训期价值", "司龄"),
            player_keywords=("正式员工", "司龄", "培训费", "赔偿"),
        ),
    ),
}


def initial_game_point_id(scene_id: str) -> str | None:
    rules = _rules_for_scene(scene_id)
    return rules[0].point_id if rules else None


def build_voice_round_guidance(session_state: SessionState) -> str:
    if session_state.interaction_mode != "voice":
        return ""

    parts: list[str] = []
    active_rule = _rule_by_point_id(session_state.scene_id, session_state.active_game_point_id) or _rule_for_round(session_state)
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
    active_rule = _rule_by_point_id(session_state.scene_id, session_state.active_game_point_id)

    if active_rule and _player_resolved(active_rule, player):
        return GamePointHint(
            point_id=active_rule.point_id,
            trap_type=active_rule.trap_type,
            explanation=_resolved_explanation(active_rule, delta),
            status="resolved",
        )

    for rule in _rules_for_scene(session_state.scene_id):
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

    active_rule = _rule_by_point_id(session_state.scene_id, session_state.active_game_point_id)
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
    elif active_rule.point_id == "gp_ops_perf_split":
        buffed.info_exposure = max(-12, buffed.info_exposure - 5)
        buffed.salary_offer = min(4000, buffed.salary_offer + 800)
    elif active_rule.point_id == "gp_ops_social_base":
        buffed.hr_patience = max(-15, buffed.hr_patience - 3)
        buffed.info_exposure = max(-12, buffed.info_exposure - 4)
    elif active_rule.point_id == "gp_ops_level_anchor":
        buffed.hr_patience = max(-15, buffed.hr_patience - 4)
        buffed.salary_offer = min(4000, buffed.salary_offer + 1000)
    elif active_rule.point_id == "gp_ops_quarter_bonus":
        buffed.info_exposure = max(-12, buffed.info_exposure - 4)
    elif active_rule.point_id == "gp_ops_batch_pressure":
        buffed.hr_patience = max(-15, buffed.hr_patience - 2)
        buffed.info_exposure = max(-12, buffed.info_exposure - 5)
    elif active_rule.point_id == "gp_trainee_total_package":
        buffed.info_exposure = max(-12, buffed.info_exposure - 5)
    elif active_rule.point_id == "gp_trainee_non_compete":
        buffed.hr_patience = max(-15, buffed.hr_patience - 3)
    elif active_rule.point_id == "gp_trainee_rotation":
        buffed.info_exposure = max(-12, buffed.info_exposure - 4)
    elif active_rule.point_id == "gp_trainee_signing":
        buffed.salary_offer = min(3000, buffed.salary_offer + 500)
    elif active_rule.point_id == "gp_trainee_identity":
        buffed.hr_patience = max(-15, buffed.hr_patience - 2)
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


def _rule_by_point_id(scene_id: str, point_id: str | None) -> GamePointRule | None:
    if not point_id:
        return None
    for rule in _rules_for_scene(scene_id):
        if rule.point_id == point_id:
            return rule
    return None


def _rule_for_round(session_state: SessionState) -> GamePointRule | None:
    unresolved = [rule for rule in _rules_for_scene(session_state.scene_id) if rule.point_id not in session_state.resolved_game_points]
    if not unresolved:
        return None
    index = min(max(session_state.round_index - 1, 0) // 2, len(unresolved) - 1)
    return unresolved[index]


def _next_unresolved_point_id(session_state: SessionState) -> str | None:
    for rule in _rules_for_scene(session_state.scene_id):
        if rule.point_id not in session_state.resolved_game_points:
            return rule.point_id
    return None


def _rules_for_scene(scene_id: str) -> tuple[GamePointRule, ...]:
    return VOICE_GAME_POINTS.get(scene_id, VOICE_GAME_POINTS["scene_001"])


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
    if rule.point_id == "gp_ops_perf_split":
        return "你把绩效和保底工资拆开了，后面继续把保护期和合同写实。"
    if rule.point_id == "gp_ops_social_base":
        return "你把五险一金问到具体数字了，继续盯住实际工资基数和比例。"
    if rule.point_id == "gp_ops_level_anchor":
        return "你已经挑战了岗位定级，下一步继续逼 HR 解释评定依据和带宽上沿。"
    if rule.point_id == "gp_ops_quarter_bonus":
        return "你没有吃下季度奖金画饼，下一句继续问公式和合同落地。"
    if rule.point_id == "gp_ops_batch_pressure":
        return "你稳住了批量招聘施压，继续强调自己和同批候选人的差异。"
    if rule.point_id == "gp_trainee_total_package":
        return "你拆开了大厂总包，后面继续把保底月薪和临时福利分开。"
    if rule.point_id == "gp_trainee_non_compete":
        return "你已经抓到竞业限制，下一步继续追补偿金和限制范围。"
    if rule.point_id == "gp_trainee_rotation":
        return "你把定岗画饼问穿了，接着逼 HR 说明最低保障和考核标准。"
    if rule.point_id == "gp_trainee_signing":
        return "你主动把签字费抬上桌了，后面继续拿竞品或搬家成本施压。"
    if rule.point_id == "gp_trainee_identity":
        return "你开始追培训生身份问题了，下一步继续问司龄和离职责任。"
    return "这轮你识破了 HR 的博弈点，继续把关键条件谈实。"
