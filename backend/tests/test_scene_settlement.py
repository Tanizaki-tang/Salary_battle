from __future__ import annotations

from app.api.session_routes import create_session_data
from app.modules.flow_controller.settle_service import settle_session
from app.shared_types.game_types import ConversationMessage, SessionState


def _make_session(scene_id: str, role_id: str) -> SessionState:
    data = create_session_data(
        {
            "user_id": f"user_{scene_id}",
            "user_name": "场景测试",
            "scene_id": scene_id,
            "role_id": role_id,
            "hr_personality_id": "hr_honest",
        }
    )
    return SessionState.model_validate(data["session"])


def test_ops_scene_settlement_exposes_base_and_performance_package():
    session = _make_session("scene_002", "role_ops")
    session.current_salary_offer = 13000
    session.identified_traps = ["A", "B", "D"]
    session.strategy_history = ["probe", "counter_pressure", "strong_push"]
    session.conversation_history.extend(
        [
            ConversationMessage(role="player", content="我想确认基础工资保底多少，绩效保护期和季度奖金公式能写明吗？", round_index=1),
            ConversationMessage(role="hr", content="基础 10K，绩效 3K，前 6 个月可以给保护期，季度奖按公式核算。", round_index=1),
            ConversationMessage(role="player", content="社保基数和公积金比例也请按实际工资确认。", round_index=2),
        ]
    )

    result = settle_session(session)

    assert result.scene_name == "中型企业运营岗"
    assert result.offer is not None
    assert result.offer.base_salary is not None and result.offer.base_salary >= 10000
    assert result.offer.performance_salary == 3000
    assert result.offer.performance_protection_months == 6
    assert result.offer.quarterly_bonus_clause == "公式已明确"


def test_trainee_scene_settlement_exposes_signing_bonus_and_non_compete():
    session = _make_session("scene_003", "role_trainee")
    session.current_salary_offer = 18000
    session.identified_traps = ["A", "B", "D"]
    session.strategy_history = ["probe", "counter_pressure", "strong_push"]
    session.conversation_history.extend(
        [
            ConversationMessage(role="player", content="请拆开总包，我想知道保底月薪、签字费和房补期限。", round_index=1),
            ConversationMessage(role="hr", content="如果你 offer competing 强，我们可以看看 sign-on bonus。", round_index=1),
            ConversationMessage(role="player", content="另外竞业限制的月数和补偿金标准也请说清楚。", round_index=2),
            ConversationMessage(role="player", content="如果可以的话我接受这个 offer。", round_index=3),
        ]
    )

    result = settle_session(session)

    assert result.scene_name == "大厂管培生"
    assert result.offer is not None
    assert result.offer.signing_bonus is not None and result.offer.signing_bonus >= 10000
    assert result.offer.non_compete_months == 6
    assert result.offer.housing_subsidy_months == 18
