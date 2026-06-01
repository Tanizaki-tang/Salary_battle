from __future__ import annotations

import re

from app.repositories.scene_repository import get_scene_trap_labels
from app.shared_types.game_types import OfferPackage, ScoreBreakdown, SessionState, SettleResult, SettleStats

PATIENCE_REJECT_THRESHOLD = 10
CLAUSE_RULES = [
    (
        "social_security",
        "五险社保",
        re.compile(r"(五险一金|五险|社保|社保基数|养老|医保)"),
        "五险社保基数没谈清，入职后可能按最低基数缴纳。",
    ),
    (
        "housing_fund",
        "公积金",
        re.compile(r"(公积金|住房公积金)"),
        "公积金比例没谈清，到账比例可能偏低。",
    ),
    (
        "overtime",
        "加班费",
        re.compile(r"(加班费|加班补贴|调休|补休|加班)"),
        "加班费没谈清，HR 很可能按总包或调休处理。",
    ),
    (
        "working_hours",
        "工时安排",
        re.compile(r"(工时|工作时间|上班时间|下班时间|双休|单休|大小周|996|1075|作息)"),
        "工时边界没谈清，存在隐性加班和大小周风险。",
    ),
]
PLAYER_ACCEPT_RE = re.compile(r"(接受|可以|行啊|没问题|那就这样|成交|定了|发offer|发我offer|我接|入职)")
HR_FINALIZE_RE = re.compile(r"(发offer|欢迎加入|可以入职|就按这个定|这边给你发offer|录用)")


def settle_session(session_state: SessionState) -> SettleResult:
    if session_state.scene_id == "scene_002":
        return _settle_ops_scene(session_state)
    if session_state.scene_id == "scene_003":
        return _settle_trainee_scene(session_state)

    anchors = session_state.scene_context.salary_anchor
    score_profile = session_state.scene_context.score_profile

    final_salary = max(anchors.legal_floor, min(anchors.ideal_target, session_state.current_salary_offer))

    dq_raw = (final_salary - anchors.legal_floor) / max(1, (anchors.ideal_target - anchors.legal_floor)) * 100
    dq = int(max(0, min(100, dq_raw)))
    td = int(
        max(
            0,
            min(
                100,
                (len(session_state.identified_traps) / 5) * 100
                + session_state.law_citation_count * 5
                - session_state.misjudge_count * 3,
            ),
        )
    )
    wh = int(max(0, min(100, 100 - session_state.info_exposure)))
    si = int(max(0, min(100, 40 + len(session_state.identified_traps) * 10 + session_state.law_citation_count * 5)))

    final_score = int(
        dq * score_profile.dq_weight
        + td * score_profile.td_weight
        + wh * score_profile.wh_weight
        + si * score_profile.si_weight
        + score_profile.bonus_survival
    )
    if len(set(session_state.strategy_history)) >= 3:
        final_score += score_profile.bonus_strategy_diversity
    if session_state.info_exposure > score_profile.high_exposure_threshold:
        final_score -= score_profile.penalty_high_exposure
    final_score = max(0, min(110, final_score))
    grade = "A" if final_score >= score_profile.grade_a else "B" if final_score >= score_profile.grade_b else "C"

    text_blob = _conversation_text(session_state)
    discussed = _detect_discussed_clauses(session_state, text_blob)
    missed_clauses = [label for key, label, *_ in CLAUSE_RULES if not discussed[key]]
    offer_accepted = _is_offer_accepted(session_state)
    rounds_exhausted = session_state.round_index >= max(1, session_state.max_round)
    patience_collapsed = session_state.hr_patience <= PATIENCE_REJECT_THRESHOLD
    early_round_limit = max(3, min(6, session_state.max_round // 4 + 1))
    rushed_deal = offer_accepted and session_state.round_index <= early_round_limit and len(missed_clauses) >= 2

    if not offer_accepted and (patience_collapsed or rounds_exhausted):
        verdict = "rejected"
        if patience_collapsed:
            outcome_reason = "HR 好感度已经跌破底线，你还没把 offer 关键条件谈拢，最终被直接拒绝。"
        else:
            outcome_reason = "谈判轮次耗尽时，你仍未把 offer 条件真正谈实，HR 最终没有给出确认录用。"
    else:
        verdict = "hired"
        if rushed_deal:
            outcome_reason = "你过早锁定 offer，虽然拿到录用，但多个关键条款没谈清，存在明显被坑风险。"
        else:
            outcome_reason = "你在 HR 耐心耗尽前稳住了谈判节奏，顺利拿到了可落地的 offer。"

    offer = OfferPackage(
        equity_ratio=max(0.0, float(session_state.equity_ratio)),
        social_security_base="全额工资基数"
        if discussed["social_security"] or "B" in session_state.identified_traps
        else "未谈妥，存在按最低基数缴纳风险",
        housing_fund_ratio="12%"
        if discussed["housing_fund"] or "B" in session_state.identified_traps
        else "未谈妥，比例可能偏低",
        overtime_policy="单独计算"
        if discussed["overtime"] or "C" in session_state.identified_traps
        else "未谈妥，可能被默认含在总包",
        working_hours_agreement="双休/工时写入 offer"
        if discussed["working_hours"] or "D" in session_state.identified_traps
        else "未谈妥，存在隐性加班风险",
    )
    risk_notes = _build_risk_notes(verdict=verdict, rushed_deal=rushed_deal, missed_clauses=missed_clauses)

    return SettleResult(
        final_salary=final_salary,
        final_score=final_score,
        grade=grade,
        review_tip=build_review_tip(
            final_score=final_score,
            dq=dq,
            td=td,
            wh=wh,
            si=si,
            session_state=session_state,
        ),
        verdict=verdict,
        outcome_reason=outcome_reason,
        title=_build_title(verdict=verdict, rushed_deal=rushed_deal, grade=grade),
        medal=_build_medal(verdict=verdict, rushed_deal=rushed_deal, grade=grade),
        scene_name=session_state.scene_context.meta.scene_name,
        summary=_build_summary(
            verdict=verdict,
            rushed_deal=rushed_deal,
            final_salary=final_salary,
            missed_clauses=missed_clauses,
        ),
        risk_notes=risk_notes,
        missed_clauses=missed_clauses,
        breakdown=ScoreBreakdown(dq=dq, td=td, wh=wh, si=si),
        offer=offer,
        stats=SettleStats(
            traps_identified=len(session_state.identified_traps),
            traps_total=5,
            trap_labels=_trap_labels_for_scene(session_state),
            law_citation_count=session_state.law_citation_count,
            strategy_count=len(set(session_state.strategy_history)),
            final_patience=session_state.hr_patience,
        ),
    )


def build_review_tip(
    *,
    final_score: int,
    dq: int,
    td: int,
    wh: int,
    si: int,
    session_state: SessionState,
) -> str:
    if session_state.info_exposure > session_state.scene_context.score_profile.high_exposure_threshold:
        return "你在谈判里暴露了太多底牌，后面要更克制地给信息，别让 HR 轻松拿捏节奏。"
    if final_score >= 85:
        return "这轮谈得很老练，既保住了薪资，也能持续追问关键条款，整体节奏控制得不错。"
    if td < 35:
        return "陷阱识别偏弱，后面要更主动追问加班费、五险一金和工时边界，别只盯着薪资。"
    weakest = min(("成交质量", dq), ("陷阱识别", td), ("工时目标", wh), ("社保匹配", si), key=lambda item: item[1])[0]
    return f"这局还有提升空间，当前最短板是{weakest}，下次建议围绕关键条款多追问两轮。"


def _conversation_text(session_state: SessionState) -> str:
    return "\n".join((msg.content or "").strip() for msg in session_state.conversation_history if (msg.content or "").strip())


def _detect_discussed_clauses(session_state: SessionState, text_blob: str) -> dict[str, bool]:
    detected: dict[str, bool] = {}
    trap_set = set(session_state.identified_traps)
    for key, _label, pattern, _risk in CLAUSE_RULES:
        discussed = bool(pattern.search(text_blob))
        if key in {"social_security", "housing_fund"} and "B" in trap_set:
            discussed = True
        if key == "overtime" and "C" in trap_set:
            discussed = True
        if key == "working_hours" and "D" in trap_set:
            discussed = True
        detected[key] = discussed
    return detected


def _is_offer_accepted(session_state: SessionState) -> bool:
    for msg in session_state.conversation_history[1:]:
        content = (msg.content or "").strip()
        if not content:
            continue
        if msg.role == "player" and PLAYER_ACCEPT_RE.search(content):
            return True
        if msg.role == "hr" and msg.round_index > 0 and HR_FINALIZE_RE.search(content):
            return True
    return False


def _build_risk_notes(*, verdict: str, rushed_deal: bool, missed_clauses: list[str]) -> list[str]:
    notes: list[str] = []
    if verdict == "rejected":
        notes.append("本局没有在 HR 耐心耗尽前把录用条件谈实，结果直接转为拒绝。")
    if rushed_deal:
        notes.append("你成交得太快，offer 里仍有多个隐性坑位需要补谈。")
    for key, label, _pattern, risk in CLAUSE_RULES:
        if label in missed_clauses:
            notes.append(risk)
    return notes


def _build_title(*, verdict: str, rushed_deal: bool, grade: str) -> str:
    if verdict == "rejected":
        return "谈崩出局"
    if rushed_deal:
        return "带坑录用"
    if grade == "A":
        return "稳准狠拿 Offer"
    if grade == "B":
        return "稳住节奏拿 Offer"
    return "惊险过关"


def _build_medal(*, verdict: str, rushed_deal: bool, grade: str) -> str:
    if verdict == "rejected":
        return "💥"
    if rushed_deal:
        return "⚠️"
    return "🏆" if grade == "A" else "🎯"


def _build_summary(*, verdict: str, rushed_deal: bool, final_salary: int, missed_clauses: list[str]) -> str:
    salary_k = round(final_salary / 1000, 1)
    if verdict == "rejected":
        return f"你一度把月薪谈到 {salary_k}K，但在 HR 耐心见底前没把 offer 条件锁死，最终遗憾出局。"
    if rushed_deal and missed_clauses:
        missed = "、".join(missed_clauses[:3])
        return f"你拿到了 {salary_k}K 的录用，但因为过早成交，{missed} 这些关键条款还没谈清。"
    return f"你成功把 offer 落到 {salary_k}K，并且把关键风险点谈得比较扎实。"


def _settle_ops_scene(session_state: SessionState) -> SettleResult:
    anchors = session_state.scene_context.salary_anchor
    final_salary = max(anchors.legal_floor, min(anchors.ideal_target, session_state.current_salary_offer))
    base_salary = max(7000, min(12000, final_salary - 3000))
    performance_salary = max(2000, final_salary - base_salary)
    text_blob = _conversation_text(session_state)
    discussed = _detect_discussed_clauses(session_state, text_blob)
    discussed_performance = bool(re.search(r"(绩效|保底|保底月薪|KPI|系数)", text_blob))
    discussed_quarterly = bool(re.search(r"(季度奖|季度奖金|奖金公式|年终奖)", text_blob))
    discussed_probation = bool(re.search(r"(试用期|打八折|缩短试用期)", text_blob))

    dq = int(max(0, min(100, (base_salary - 5000) / 7000 * 100)))
    td = int(max(0, min(100, (len(session_state.identified_traps) / 5) * 100 + session_state.law_citation_count * 5)))
    wh = 0
    if discussed_performance or "A" in session_state.identified_traps:
        wh += 40
    if discussed_quarterly or "D" in session_state.identified_traps:
        wh += 30
    if discussed["overtime"]:
        wh += 30
    si = 0
    if discussed["social_security"] or "B" in session_state.identified_traps:
        si += 70
    if discussed["housing_fund"]:
        si += 30
    si = int(max(0, min(100, si * 1.2)))

    final_score = int(dq * 0.35 + td * 0.25 + wh * 0.20 + si * 0.20 + 5)
    if len(set(session_state.strategy_history)) >= 3:
        final_score += 5
    if session_state.info_exposure > 80:
        final_score -= 10
    final_score = max(0, min(110, final_score))
    grade = "A" if final_score >= 80 else "B" if final_score >= 60 else "C"

    verdict, outcome_reason, rushed_deal, missed_clauses = _resolve_common_outcome(session_state, discussed, extra_missed=["绩效保底", "季度奖金"] if not discussed_performance or not discussed_quarterly else [])
    performance_protection = 6 if discussed_performance or "A" in session_state.identified_traps else 0
    risk_notes = _build_risk_notes(verdict=verdict, rushed_deal=rushed_deal, missed_clauses=missed_clauses)
    if not discussed_probation:
        risk_notes.append("试用期折薪或保护期没谈实，前 3 个月实际到手可能继续被压。")

    return SettleResult(
        final_salary=final_salary,
        final_score=final_score,
        grade=grade,
        review_tip=_build_ops_review_tip(final_score=final_score, td=td, wh=wh, si=si),
        verdict=verdict,
        outcome_reason=outcome_reason,
        title="体系内抬价成功" if verdict == "hired" and grade == "A" else ("压价反杀" if verdict == "hired" else "体系压崩"),
        medal="🥇" if verdict == "hired" and grade == "A" else ("🎯" if verdict == "hired" else "💥"),
        scene_name=session_state.scene_context.meta.scene_name,
        summary=_build_ops_summary(
            verdict=verdict,
            base_salary=base_salary,
            performance_salary=performance_salary,
            performance_protection=performance_protection,
        ),
        risk_notes=risk_notes,
        missed_clauses=missed_clauses,
        breakdown=ScoreBreakdown(dq=dq, td=td, wh=wh, si=si),
        offer=OfferPackage(
            equity_ratio=0.0,
            social_security_base="按实际工资全额缴纳" if discussed["social_security"] or "B" in session_state.identified_traps else "按最低基数缴纳风险较高",
            housing_fund_ratio="7%" if discussed["housing_fund"] else "5% 默认档",
            overtime_policy="有明确补偿机制" if discussed["overtime"] else "默认灵活处理，不单独计算",
            working_hours_agreement="工时与试用期边界已确认" if discussed["working_hours"] or discussed_probation else "工时/试用期边界仍偏模糊",
            base_salary=base_salary,
            performance_salary=performance_salary,
            annual_bonus_months=13,
            performance_protection_months=performance_protection,
            quarterly_bonus_clause="公式已明确" if discussed_quarterly or "D" in session_state.identified_traps else "仅口头承诺，未写实",
            package_note="运营岗核心不只是总包，而是基础工资、绩效保护期和岗位定级。",
        ),
        stats=SettleStats(
            traps_identified=len(session_state.identified_traps),
            traps_total=5,
            trap_labels=_trap_labels_for_scene(session_state),
            law_citation_count=session_state.law_citation_count,
            strategy_count=len(set(session_state.strategy_history)),
            final_patience=session_state.hr_patience,
        ),
    )


def _settle_trainee_scene(session_state: SessionState) -> SettleResult:
    anchors = session_state.scene_context.salary_anchor
    final_salary = max(anchors.legal_floor, min(18000, session_state.current_salary_offer))
    text_blob = _conversation_text(session_state)
    discussed = _detect_discussed_clauses(session_state, text_blob)
    discussed_compete = bool(re.search(r"(竞业|竞业限制|补偿金|竞业补偿)", text_blob))
    discussed_signing = bool(re.search(r"(签字费|sign[ -]?on|签约费|一次性补贴|搬家费)", text_blob, re.I))
    discussed_housing = bool(re.search(r"(房补|住房补贴|延长房补)", text_blob))
    discussed_identity = bool(re.search(r"(培训生|正式员工|司龄|培训费|离职赔偿)", text_blob))

    signing_bonus = 0
    if discussed_signing or "D" in session_state.identified_traps:
        signing_bonus = 10000 if len(session_state.identified_traps) < 3 else 20000
    non_compete_months = 6 if discussed_compete or "B" in session_state.identified_traps else 12
    housing_subsidy_months = 18 if discussed_housing or "A" in session_state.identified_traps else 12

    dq = int(max(0, min(100, (final_salary - 10000) / 12000 * 100)))
    td = int(max(0, min(100, (len(session_state.identified_traps) / 5) * 100)))
    welfare = min(100, (signing_bonus // 5000) * 20 + max(0, (12 - non_compete_months) // 2) * 15 + max(0, (housing_subsidy_months - 12) // 3) * 10)
    relationship = max(0, min(100, session_state.hr_patience))
    final_score = int(dq * 0.25 + td * 0.30 + welfare * 0.25 + relationship * 0.20)
    if len(set(session_state.strategy_history)) >= 3:
        final_score += 5
    if session_state.info_exposure > 80:
        final_score -= 10
    final_score = max(0, min(110, final_score))
    grade = "A" if final_score >= 80 else "B" if final_score >= 60 else "C"

    verdict, outcome_reason, rushed_deal, missed_clauses = _resolve_common_outcome(
        session_state,
        discussed,
        extra_missed=["竞业限制", "签字费/搬家补贴", "培训生身份"] if not (discussed_compete and discussed_signing and discussed_identity) else [],
    )
    risk_notes = _build_risk_notes(verdict=verdict, rushed_deal=rushed_deal, missed_clauses=missed_clauses)
    if not discussed_identity:
        risk_notes.append("培训生身份和司龄计算没问清，后续定岗和离职成本可能比你想象更高。")

    return SettleResult(
        final_salary=final_salary,
        final_score=final_score,
        grade=grade,
        review_tip=_build_trainee_review_tip(final_score=final_score, td=td, welfare=welfare),
        verdict=verdict,
        outcome_reason=outcome_reason,
        title="流程里抠出空间" if verdict == "hired" and grade == "A" else ("保底上岸" if verdict == "hired" else "流程淘汰"),
        medal="🥇" if verdict == "hired" and grade == "A" else ("🎓" if verdict == "hired" else "💥"),
        scene_name=session_state.scene_context.meta.scene_name,
        summary=_build_trainee_summary(
            verdict=verdict,
            final_salary=final_salary,
            signing_bonus=signing_bonus,
            non_compete_months=non_compete_months,
        ),
        risk_notes=risk_notes,
        missed_clauses=missed_clauses,
        breakdown=ScoreBreakdown(dq=dq, td=td, wh=welfare, si=relationship),
        offer=OfferPackage(
            equity_ratio=0.0,
            social_security_base="按实际工资全额缴纳",
            housing_fund_ratio="12%",
            overtime_policy="大厂流程制，需在定岗后继续确认",
            working_hours_agreement="培训期和轮岗安排已说明" if discussed_identity else "培训期/定岗边界仍偏模糊",
            signing_bonus=signing_bonus,
            non_compete_months=non_compete_months,
            housing_subsidy_months=housing_subsidy_months,
            package_note="大厂管培真正能谈的往往不是月薪，而是签字费、竞业条款和福利延续。",
        ),
        stats=SettleStats(
            traps_identified=len(session_state.identified_traps),
            traps_total=5,
            trap_labels=_trap_labels_for_scene(session_state),
            law_citation_count=session_state.law_citation_count,
            strategy_count=len(set(session_state.strategy_history)),
            final_patience=session_state.hr_patience,
        ),
    )


def _resolve_common_outcome(
    session_state: SessionState,
    discussed: dict[str, bool],
    *,
    extra_missed: list[str] | None = None,
) -> tuple[str, str, bool, list[str]]:
    missed_clauses = [label for key, label, *_ in CLAUSE_RULES if not discussed[key]]
    if extra_missed:
        for item in extra_missed:
            if item not in missed_clauses:
                missed_clauses.append(item)
    offer_accepted = _is_offer_accepted(session_state)
    rounds_exhausted = session_state.round_index >= max(1, session_state.max_round)
    patience_collapsed = session_state.hr_patience <= PATIENCE_REJECT_THRESHOLD
    early_round_limit = max(3, min(6, session_state.max_round // 4 + 1))
    rushed_deal = offer_accepted and session_state.round_index <= early_round_limit and len(missed_clauses) >= 2
    if not offer_accepted and (patience_collapsed or rounds_exhausted):
        if patience_collapsed:
            return "rejected", "HR 耐心跌穿底线前，你还没把关键条件锁实，流程直接中止。", rushed_deal, missed_clauses
        return "rejected", "谈判轮次耗尽时，关键条款仍是模糊状态，HR 没有确认最终录用。", rushed_deal, missed_clauses
    if rushed_deal:
        return "hired", "你虽然拿到了录用，但多个核心条款仍停留在口头层面，后续存在明显风险。", rushed_deal, missed_clauses
    return "hired", "你在流程结束前把关键条件谈到了可执行层，成功拿到更扎实的 offer。", rushed_deal, missed_clauses


def _trap_labels_for_scene(session_state: SessionState) -> list[str]:
    scene_map = get_scene_trap_labels(session_state.scene_id)
    return [scene_map[t] for t in session_state.identified_traps if t in scene_map]


def _build_ops_review_tip(*, final_score: int, td: int, wh: int, si: int) -> str:
    if final_score >= 85:
        return "你把运营岗最容易被包装的部分拆开了，基础工资、绩效和基数都谈得比较清楚。"
    if wh < 50:
        return "这局最大短板是绩效结构没拆透，下次先盯住保底月薪和绩效保护期。"
    if si < 50:
        return "你对五险一金和基数追问不够，中型企业最容易在这里留坑。"
    if td < 35:
        return "体系压价和批量招聘的话术还没有完全识破，后面要更主动挑战职级和定级依据。"
    return "这局已经有雏形了，下一次继续把基础工资和季度奖金公式问到写实。"


def _build_trainee_review_tip(*, final_score: int, td: int, welfare: int) -> str:
    if final_score >= 85:
        return "你没有被大厂总包和光环带偏，成功把流程里的隐藏成本和补偿空间谈出来了。"
    if welfare < 40:
        return "这局福利侧空间挖得不够，签字费、房补延长和竞业条款其实都值得继续追问。"
    if td < 35:
        return "你拆总包和识别竞业限制的力度还不够，大厂场景最怕只看表面数字。"
    return "这局思路是对的，下一次把定岗机制和培训生身份再问透一点。"


def _build_ops_summary(*, verdict: str, base_salary: int, performance_salary: int, performance_protection: int) -> str:
    if verdict == "rejected":
        return f"你一度把运营岗月包谈到 {base_salary + performance_salary} 元，但基础工资和绩效保护还没锁死，最终没能拿下。"
    if performance_protection:
        return f"你把运营岗谈到了基础 {base_salary} 元 + 绩效 {performance_salary} 元，并额外争到了 {performance_protection} 个月绩效保护期。"
    return f"你把运营岗谈到了基础 {base_salary} 元 + 绩效 {performance_salary} 元，但绩效保底仍建议入职前继续补谈。"


def _build_trainee_summary(*, verdict: str, final_salary: int, signing_bonus: int, non_compete_months: int) -> str:
    salary_k = round(final_salary / 1000, 1)
    if verdict == "rejected":
        return f"你识别出了一部分大厂总包水分，但还没来得及把竞业和流程空间谈实，最终止步于 {salary_k}K 月薪口径。"
    if signing_bonus > 0:
        return f"你把月薪稳在 {salary_k}K，还额外撬出了 {signing_bonus / 1000:.0f}K 签字费，并把竞业限制压到了 {non_compete_months} 个月。"
    return f"你拿到了 {salary_k}K 的管培 offer，并把竞业与福利细节问到了更可控的范围。"
