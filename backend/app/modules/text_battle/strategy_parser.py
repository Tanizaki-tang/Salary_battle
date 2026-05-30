from __future__ import annotations

from app.shared_types.game_types import TextTurnPayload


def normalize_strategy(payload: TextTurnPayload) -> str:
    """
    输入:
    - payload.strategy: 可选策略值
    - payload.player_text: 可选自由文本

    输出:
    - 标准化策略字符串: strong_push/probe/concede/counter_pressure

    示例:
    - 输入 {"strategy":"probe"} -> 输出 "probe"
    - 输入 {"player_text":"我想确认薪资区间"} -> 输出 "probe"
    """
    if payload.strategy:
        return payload.strategy
    if payload.player_text:
        return "probe"
    return "concede"
