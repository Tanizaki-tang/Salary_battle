from __future__ import annotations

from app.shared_types.card_game_types import CardStrategyId

STRATEGY_SPECS: dict[CardStrategyId, str] = {
    "strong_push": "强硬要求：直接表达不满，展示筹码，要求涨薪，语气坚定",
    "probe": "信息搜集：追问细节、摸底牌、了解工时与保障，语气理性",
    "concede": "温和协商：先认同对方再提诉求，缓和气氛，语气合作",
    "counter_pressure": "反客为主：用反问或对比打乱 HR 节奏，逼出真实预算",
    "expose_rhetoric": "拆穿话术：点破模糊表述，要求写入合同，语气犀利但专业",
    "off_topic": "非谈判内容：短暂闲聊或转移话题救场，不直接推条件",
}

ALL_STRATEGIES: tuple[CardStrategyId, ...] = (
    "strong_push",
    "probe",
    "concede",
    "counter_pressure",
    "expose_rhetoric",
    "off_topic",
)

OPTION_FALLBACK: dict[CardStrategyId, str] = {
    "strong_push": "我希望薪资能再往上谈一档，15K 和我的预期还有差距。",
    "probe": "方便把 base、绩效和加班规则拆开说明一下吗？",
    "concede": "整体方向我能接受，我们看看还有哪些细节可以微调。",
    "counter_pressure": "如果预算有限，你们最灵活的是薪资还是工时这块？",
    "expose_rhetoric": "「弹性工作制」具体怎么算？我希望关键条款写进 offer。",
    "off_topic": "听说团队氛围不错，你们平时协作节奏大概是怎样的？",
}
