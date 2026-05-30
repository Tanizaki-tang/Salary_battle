from __future__ import annotations

from app.modules.flow_controller.phase_policy import decide_next_phase_with_policy
from app.shared_types.game_types import FlowDecision, NextPhase, SessionState


def decide_next_phase(session_state: SessionState, agent_next_phase_hint: NextPhase | None = None) -> FlowDecision:
    """
    输入:
    - session_state: 已更新的会话状态

    输出:
    - FlowDecision: 下一阶段 text/voice/end

    规则:
    - 满足终局条件 -> end
    - 对话中后期且 HR 耐心较低，或玩家连续强硬 -> voice
    - 其他 -> text
    """
    return decide_next_phase_with_policy(session_state, agent_next_phase_hint)
