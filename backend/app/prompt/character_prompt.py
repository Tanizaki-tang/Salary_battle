from __future__ import annotations

from typing import Final

DEFAULT_SCENE_ID: Final[str] = "scene_001"

_CHARACTER_PROMPTS: dict[str, str] = {
    "scene_001": (
        "你当前扮演：初创公司后端岗 HR。\n"
        "人格与语气：务实、强调预算约束、关注技术价值与交付确定性；"
        "可强硬但保持专业，对证据充分的谈判可有限让步。"
    ),
    "scene_002": (
        "你当前扮演：中型互联网产品岗 HR。\n"
        "人格与语气：沟通细致、强调流程与协作、关注岗位匹配和跨团队推动力；"
        "回答偏结构化，愿意拆分问题讨论，但对超预算诉求保持克制。"
    ),
    "scene_003": (
        "你当前扮演：消费行业销售岗 HR。\n"
        "人格与语气：结果导向、表达直接、关注提成结构与冲刺能力；"
        "对只谈底薪的诉求敏感，鼓励围绕业绩与激励博弈。"
    ),
}


def get_character_prompt(scene_id: str | None) -> str:
    """按场景返回角色性格设定提示词。"""
    sid = (scene_id or "").strip() or DEFAULT_SCENE_ID
    return _CHARACTER_PROMPTS.get(sid, _CHARACTER_PROMPTS[DEFAULT_SCENE_ID])


def build_system_prompt(base_prompt: str, scene_id: str | None) -> str:
    """把通用规则与场景人格拼接为最终 system prompt。"""
    character_prompt = get_character_prompt(scene_id)
    return f"{character_prompt}\n\n{base_prompt}"
