from __future__ import annotations

from typing import Final

from app.prompt.hr_personality import get_personality_prompt
from app.prompt.scenario_loader import load_hr_system_prompt
from app.prompt.traps_prompt import get_traps_prompt

DEFAULT_SCENE_ID: Final[str] = "scene_001"
GM_SCENE_IDS: Final[frozenset[str]] = frozenset({"scene_001", "scenario_001"})

_SCENE_PROMPTS: dict[str, str] = {
    "scene_001": (
        "你当前服务的谈判场景：初创公司后端岗。\n"
        "公司背景：A轮 AI/大模型创业公司，50-100人，预算偏紧但重视技术人才。\n"
        "你的任务：在控制用人成本的前提下完成 offer 谈判，并维护公司雇主形象。"
    ),
    "scene_002": (
        "你当前服务的谈判场景：中型互联网产品岗。\n"
        "公司背景：流程规范、强调跨团队协作与岗位匹配度。\n"
        "你的任务：围绕职级与绩效体系解释 offer，避免超预算承诺。"
    ),
    "scene_003": (
        "你当前服务的谈判场景：消费行业销售岗。\n"
        "公司背景：结果导向，底薪+提成结构，关注业绩冲刺能力。\n"
        "你的任务：引导候选人关注整体激励 package，而非只谈底薪。"
    ),
}


def _resolve_scene_id(scene_id: str | None) -> str:
    return (scene_id or "").strip() or DEFAULT_SCENE_ID


def get_scene_prompt(scene_id: str | None) -> str:
    sid = _resolve_scene_id(scene_id)
    if sid in GM_SCENE_IDS:
        try:
            return load_hr_system_prompt()
        except Exception:
            pass
    return _SCENE_PROMPTS.get(sid, _SCENE_PROMPTS[DEFAULT_SCENE_ID])


def get_character_prompt(scene_id: str | None) -> str:
    """兼容旧调用：仅返回场景设定。"""
    return get_scene_prompt(scene_id)


def build_system_prompt(base_prompt: str, scene_id: str | None, personality_id: str | None = None) -> str:
    """把场景、HR人格、陷阱规则与通用规则拼接为最终 system prompt。"""
    sid = _resolve_scene_id(scene_id)
    scene_prompt = get_scene_prompt(scene_id)
    personality_prompt = get_personality_prompt(personality_id)
    if sid in GM_SCENE_IDS:
        traps_prompt = ""
    else:
        traps_prompt = get_traps_prompt(scene_id)
    parts = [scene_prompt, personality_prompt, traps_prompt, base_prompt]
    return "\n\n".join(p for p in parts if p.strip())
