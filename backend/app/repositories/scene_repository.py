from __future__ import annotations

from app.shared_types.game_types import (
    InitialState,
    SceneContext,
    SceneMeta,
    ScoreProfile,
    SalaryAnchor,
    StrategyType,
    TurnDelta,
)


ROLE_TO_SCENE = {
    "role_backend": "scene_001",
    "role_product": "scene_002",
    "role_sales": "scene_003",
}


def _build_scene(
    scene_id: str,
    scene_name: str,
    role_hint: str,
    opening_line: str,
    salary_anchor: SalaryAnchor,
    initial_state: InitialState,
    score_profile: ScoreProfile,
    tone_map: dict[StrategyType, str],
    strategy_delta_map: dict[StrategyType, TurnDelta],
) -> SceneContext:
    return SceneContext(
        meta=SceneMeta(scene_id=scene_id, scene_name=scene_name, role_hint=role_hint),
        opening_line=opening_line,
        initial_state=initial_state,
        salary_anchor=salary_anchor,
        score_profile=score_profile,
        tone_map=tone_map,
        strategy_delta_map=strategy_delta_map,
    )


SCENE_REGISTRY: dict[str, SceneContext] = {
    "scene_001": _build_scene(
        scene_id="scene_001",
        scene_name="初创公司后端岗",
        role_hint="后端开发求职者",
        opening_line="你好！我们给你的初始 offer 是 15K*14，你怎么看？",
        salary_anchor=SalaryAnchor(legal_floor=8000, market_fair=18000, ideal_target=25000, hr_initial_offer=15000),
        initial_state=InitialState(max_round=8, hr_patience=80, info_exposure=20, trap_count=0),
        score_profile=ScoreProfile(dq_weight=0.35, td_weight=0.25, wh_weight=0.20, si_weight=0.20),
        tone_map={
            "strong_push": "我们预算很紧，这个价格已经是阶段上限了。",
            "probe": "你的问题很专业，你先说说你关心的重点。",
            "concede": "你这个态度很好，我们可以往下聊细节。",
            "counter_pressure": "预算区间是有的，但我先听听你的预期。",
        },
        strategy_delta_map={
            "strong_push": TurnDelta(hr_patience=-8, info_exposure=12, trap_count=0),
            "probe": TurnDelta(hr_patience=-2, info_exposure=5, trap_count=0),
            "concede": TurnDelta(hr_patience=3, info_exposure=18, trap_count=0),
            "counter_pressure": TurnDelta(hr_patience=-3, info_exposure=-5, trap_count=1),
        },
    ),
    "scene_002": _build_scene(
        scene_id="scene_002",
        scene_name="中型互联网产品岗",
        role_hint="产品经理求职者",
        opening_line="我们先给到 13K*14，绩效另算，欢迎你提问题。",
        salary_anchor=SalaryAnchor(legal_floor=7000, market_fair=16000, ideal_target=22000, hr_initial_offer=13000),
        initial_state=InitialState(max_round=5, hr_patience=75, info_exposure=25, trap_count=0),
        score_profile=ScoreProfile(dq_weight=0.30, td_weight=0.30, wh_weight=0.20, si_weight=0.20),
        tone_map={
            "strong_push": "你的诉求我理解，但当前职级范围有限。",
            "probe": "你问得很细，我们可以拆开聊每一项。",
            "concede": "如果你倾向稳定，我们可以给流程保障。",
            "counter_pressure": "预算不是固定死的，关键看匹配度。",
        },
        strategy_delta_map={
            "strong_push": TurnDelta(hr_patience=-7, info_exposure=10, trap_count=0),
            "probe": TurnDelta(hr_patience=-1, info_exposure=3, trap_count=1),
            "concede": TurnDelta(hr_patience=4, info_exposure=14, trap_count=0),
            "counter_pressure": TurnDelta(hr_patience=-4, info_exposure=-6, trap_count=1),
        },
    ),
    "scene_003": _build_scene(
        scene_id="scene_003",
        scene_name="消费行业销售岗",
        role_hint="销售候选人",
        opening_line="底薪 8K，提成另计。你对奖金机制怎么看？",
        salary_anchor=SalaryAnchor(legal_floor=6000, market_fair=12000, ideal_target=18000, hr_initial_offer=8000),
        initial_state=InitialState(max_round=5, hr_patience=85, info_exposure=15, trap_count=0),
        score_profile=ScoreProfile(dq_weight=0.25, td_weight=0.20, wh_weight=0.20, si_weight=0.35),
        tone_map={
            "strong_push": "销售岗更看结果，底薪空间相对有限。",
            "probe": "提成规则我可以详细说，你继续问。",
            "concede": "你愿意先试跑的话，我们可以更快推进。",
            "counter_pressure": "你先说你希望的提成比例，我来对齐。",
        },
        strategy_delta_map={
            "strong_push": TurnDelta(hr_patience=-6, info_exposure=8, trap_count=0),
            "probe": TurnDelta(hr_patience=-1, info_exposure=2, trap_count=1),
            "concede": TurnDelta(hr_patience=5, info_exposure=12, trap_count=0),
            "counter_pressure": TurnDelta(hr_patience=-5, info_exposure=-4, trap_count=1),
        },
    ),
}


def resolve_scene_id(scene_id: str | None = None, role_id: str | None = None) -> str:
    if scene_id and scene_id in SCENE_REGISTRY:
        return scene_id
    if role_id and role_id in ROLE_TO_SCENE:
        return ROLE_TO_SCENE[role_id]
    return "scene_001"


def load_scene(scene_id: str) -> SceneContext:
    return SCENE_REGISTRY.get(scene_id, SCENE_REGISTRY["scene_001"])
