from __future__ import annotations

from app.shared_types.game_types import (
    OfferPackage,
    ScoreBreakdown,
    SessionState,
    SettleResult,
    SettleStats,
)

TRAP_LABELS: dict[str, str] = {
    "A": "先报价套话",
    "B": "期权画饼",
    "C": "加班费打包",
    "D": "社保模糊化",
    "E": "试用期画饼",
}


def _grade_title_medal(final_score: int) -> tuple[str, str, str]:
    if final_score >= 95:
        return "A", "🥇", "谈判大师"
    if final_score >= 85:
        return "A", "🥈", "老练求职者"
    if final_score >= 70:
        return "B", "🥉", "稳健求职者"
    if final_score >= 60:
        return "B", "📋", "可造之材"
    return "C", "📋", "入门求职者"


def build_review_tip(
    *,
    final_score: int,
    dq: int,
    td: int,
    wh: int,
    si: int,
    session_state: SessionState,
) -> str:
    profile = session_state.scene_context.score_profile
    if session_state.info_exposure > profile.high_exposure_threshold:
        return "信息暴露度过高：过早亮底或追问过多，下局注意先探预算再表态。"

    if final_score >= 80:
        if td >= 60:
            return "老练表现：陷阱识别出色，可继续用追问逼出书面条款。"
        if dq >= 75:
            return "成交质量出色，薪资接近理想区间，记得把口头承诺写进合同。"
        return "整体表现不错，建议多练「反问逼牌」组合，进一步抬升成交质量。"

    if final_score < 60:
        return "本局得分偏低：先稳住满意度，再逐步追问薪资与工时细节。"

    if not session_state.identified_traps:
        return "暂未识破 HR 话术陷阱，可多引用法条或反问具体基数与比例。"

    if wh < 50:
        return "工时与保障条款偏弱，下局优先追问加班与社保写入合同。"

    return "你成功控制了信息暴露度，建议继续提升陷阱识别稳定性。"


def _build_summary(session_state: SessionState, final_salary: int, final_score: int) -> str:
    scene_name = session_state.scene_context.meta.scene_name
    salary_k = round(final_salary / 1000)
    if final_score >= 85:
        return f"你在{scene_name}谈下了 {salary_k}K 的 offer，整体表现相当出色。"
    if final_score >= 70:
        return f"你在{scene_name}以 {salary_k}K 成交，结果稳健，还有提升空间。"
    return f"你在{scene_name}以 {salary_k}K 结束谈判，建议复盘陷阱识别与信息暴露控制。"


def settle_session(session_state: SessionState) -> SettleResult:
    """
    输入:
    - session_state: 结算时对局状态

    输出:
    - SettleResult: final_salary/final_score/grade/review_tip 及展示字段
    """
    anchors = session_state.scene_context.salary_anchor
    score_profile = session_state.scene_context.score_profile

    final_salary = max(anchors.legal_floor, min(anchors.ideal_target, session_state.current_salary_offer))

    dq_raw = (final_salary - anchors.legal_floor) / max(1, (anchors.ideal_target - anchors.legal_floor)) * 100
    dq = max(0, min(100, int(round(dq_raw))))
    td = max(
        0,
        min(
            100,
            int(round((len(session_state.identified_traps) / 5) * 100 + session_state.law_citation_count * 5 - session_state.misjudge_count * 3)),
        ),
    )
    wh = max(0, min(100, int(round(100 - session_state.info_exposure))))
    si = max(
        0,
        min(
            100,
            int(round(40 + len(session_state.identified_traps) * 10 + session_state.law_citation_count * 5)),
        ),
    )

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

    grade, medal, title = _grade_title_medal(final_score)
    if final_score < score_profile.grade_a and final_score >= score_profile.grade_b:
        grade = "B"
    elif final_score < score_profile.grade_b:
        grade = "C"

    review_tip = build_review_tip(
        final_score=final_score,
        dq=dq,
        td=td,
        wh=wh,
        si=si,
        session_state=session_state,
    )

    trap_labels = [TRAP_LABELS[tid] for tid in session_state.identified_traps if tid in TRAP_LABELS]

    return SettleResult(
        final_salary=final_salary,
        final_score=final_score,
        grade=grade,
        review_tip=review_tip,
        title=title,
        medal=medal,
        scene_name=session_state.scene_context.meta.scene_name,
        summary=_build_summary(session_state, final_salary, final_score),
        breakdown=ScoreBreakdown(dq=dq, td=td, wh=wh, si=si),
        offer=OfferPackage(
            equity_ratio=session_state.equity_ratio,
            social_security_base="按实际工资" if si >= 60 else "待确认",
            housing_fund_ratio="12%" if si >= 50 else "待确认",
            overtime_policy="单独计算" if wh >= 55 else "待确认",
            working_hours_agreement="弹性工作制，加班另算" if wh >= 55 else "未约定",
        ),
        stats=SettleStats(
            traps_identified=len(session_state.identified_traps),
            traps_total=5,
            trap_labels=trap_labels,
            law_citation_count=session_state.law_citation_count,
            strategy_count=len(set(session_state.strategy_history)),
            final_patience=session_state.hr_patience,
        ),
    )
