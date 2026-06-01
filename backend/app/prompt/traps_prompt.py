from __future__ import annotations

from typing import Final

from app.repositories.scene_repository import get_scene_spec

DEFAULT_SCENE_ID: Final[str] = "scene_001"
TRAP_RULES_FOOTER: Final[str] = """
        ### 陷阱检测规则（AI 内部）

        AI 在每轮回复后需要判断：**玩家本轮是否识破了某个陷阱？**

        判断标准：
        1. 玩家直接指出了陷阱的不合理性
        2. 玩家采取了正确应对中的策略
        3. 玩家引用了相关法律条款

        如果判定识破→本轮陷阱计数+1，相关知识卡解锁，HR在下一轮中调整策略（不再用同一套路）。

        > ⚠️ 同一陷阱只计算一次。如果玩家反复识破同一陷阱，只计第一次。
"""


def _build_trap_section(scene_id: str) -> str:
    spec = get_scene_spec(scene_id)
    traps = spec.get("traps", [])
    lines = [f"        ### {len(traps)} 个预设博弈点-{spec['scene_name']}"]
    for trap in traps:
        talking_points = "、".join(trap["talking_points"])
        lines.extend(
            [
                f"        #### 陷阱 {trap['trap_id']}：{trap['label']}",
                f"        - **话术方向**：{talking_points}",
                f"        - **陷阱本质**：{trap['essence']}",
                f"        - **玩家识破标志**：{trap['player_break_signal']}",
                f"        - **被识破后 HR 如何应对**：{trap['hr_adjustment_after_break']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()

def get_traps_prompt(scene_id: str | None) -> str:
    sid = (scene_id or "").strip() or DEFAULT_SCENE_ID
    body = _build_trap_section(sid)
    return f"{body}\n\n{TRAP_RULES_FOOTER}".rstrip()
