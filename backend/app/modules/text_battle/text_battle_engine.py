from __future__ import annotations

from openai import OpenAI

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, LLM_TIMEOUT
from app.contracts.text_battle_contract import TextBattleContract
from app.modules.text_battle.scenario_loader import load_hr_system_prompt, load_opening_template
from app.shared_types.game_types import SessionState, TextTurnPayload, TurnDelta, TurnResult


# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

STRATEGY_CLASSIFY_SYSTEM = """你是薪资谈判游戏的策略分类器。根据玩家发言判断策略类型。

策略定义：
- strong_push: 直接表达不满、要求涨薪、展示筹码（"太低了""我有其他offer""市场价是XX"）
- probe: 通过提问获取信息，不直接表态（"能说说薪资结构吗""绩效怎么算""期权具体多少"）
- concede: 表达认同后再提小要求（"我可以考虑，不过""如果XX就更好了""我理解公司限制"）
- counter_pressure: 把问题抛回给对方，要求对方先亮底牌（"你们的预算范围是""最高能给到多少"）
- legal_quote: 引用法律条款支撑诉求（提到劳动法、劳动合同法、社保法、加班费标准等）
- trap_detect: 准确识破HR话术中的陷阱并指出来（"你这是想套我的底牌""期权未上市价值为零""按标准来是什么意思"）

你必须且只能回复以下英文标签之一：strong_push, probe, concede, counter_pressure, legal_quote, trap_detect
不要回复中文，不要回复任何其他内容。"""


def _load_scenario_prompt() -> str:
    """加载场景 System Prompt。失败时返回简化版兜底。"""
    try:
        return load_hr_system_prompt()
    except Exception:
        return """你是薪资谈判游戏中的HR。
- 姓名：张敏，A轮AI初创公司HR负责人，热情亲和、圆滑老练
- 策略：用期权、成长空间、公司前景替代现金
- 预算：初始报价15K，实际最高22K，每一步让步都要显得"困难"
- 规则：不先报上限、先套对方期望、耐心<30时强硬、第4轮起推进成交
- 控制在80字以内，只返回回复文本"""


HR_REPLY_SYSTEM = _load_scenario_prompt()


class TextBattleEngine(TextBattleContract):
    """文本谈判引擎 — 调用 DeepSeek LLM 进行策略分类和 HR 回复生成。"""

    # ---- 策略 → delta 映射（满意度, 暴露度, 陷阱数） ----
    BASE_DELTA: dict[str, tuple[int, int, int]] = {
        "strong_push":      (-10,  8, 0),
        "probe":            (-3,   3, 0),
        "concede":          (6,   12, 0),
        "counter_pressure": (-5,  -8, 0),
        "legal_quote":      (-3,  -1, 0),
        "trap_detect":      (-5,  -6, 1),
    }

    # ---- LLM 不可用时的兜底回复 ----
    _FALLBACK_REPLIES: dict[str, str] = {
        "strong_push":      "我理解你的期望，但坦白说作为A轮公司，现金确实没法跟大厂比。不过我们期权池比较充裕，你要不要了解一下？",
        "probe":            "你说得挺细的，这样很好。具体你比较关注哪一块？薪资结构、期权、还是福利？",
        "concede":          "很高兴你能认可我们。那我帮你争取一下好的方案，你对哪方面比较在意？",
        "counter_pressure": "嗯…这个岗位的预算区间大概在12K到18K之间，具体看你最终的综合package。",
        "legal_quote":      "你说的对，法律规定的我们肯定会遵守。能在合同里明确的我们都可以写进去。",
        "trap_detect":      "哈哈你挺专业的。好吧那我直说了，我们坦诚一点，你对薪资的具体期望是多少？",
    }

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
            timeout=LLM_TIMEOUT,
        )

    # ------------------------------------------------------------------
    #  公开方法
    # ------------------------------------------------------------------

    def generate_opening(self) -> str:
        """调用 LLM 生成 HR 开场白。失败返回兜底。"""
        import random

        styles = [
            "你是张敏，A轮AI初创公司HR负责人。热情亲和地开场，提一下15K*14薪的offer，问问对方想法。40字以内。",
            "你是张敏，HR负责人。先夸一下候选人的面试表现，再自然地报出15K*14的offer。40字以内。",
            "你是张敏，A轮创业公司HR。坦诚地说公司虽然薪水不是最高的，但成长空间大，报出15K*14。40字以内。",
            "你是张敏，HR负责人。用轻松的语气恭喜候选人，然后报出15K*14薪的offer，询问看法。40字以内。",
        ]
        prompt = random.choice(styles)
        try:
            resp = self._client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.9,
                max_tokens=60,
            )
            reply = (resp.choices[0].message.content or "").strip()
            if reply:
                return reply
        except Exception:
            pass
        return load_opening_template()

    # ------------------------------------------------------------------
    #  Contract 实现
    # ------------------------------------------------------------------

    def parse_strategy(self, text_payload: TextTurnPayload) -> str:
        """解析玩家策略。

        优先级：payload.strategy 显式值 > LLM 分类 > 兜底 probe。
        """
        if text_payload.strategy:
            return text_payload.strategy

        if text_payload.player_text:
            strategy = self._classify_with_llm(text_payload.player_text)
            if strategy:
                return strategy

        return "probe"

    def run_text_turn(
        self, session_state: SessionState, text_payload: TextTurnPayload,
    ) -> TurnResult:
        """执行一个文本回合。"""
        strategy = self.parse_strategy(text_payload)
        hr_reply = self._generate_hr_reply(strategy, text_payload.player_text or "", session_state)
        delta = self._compute_delta(strategy, session_state)
        current_calculated_patience = session_state.hr_patience + delta.hr_patience
        is_over = (current_calculated_patience <= 0) or (session_state.round_index >= session_state.max_round)
        next_round_index = session_state.round_index + 1
        return TurnResult(
            hr_reply=hr_reply,
            delta=delta,
            is_trap_hit=delta.trap_count > 0,
            is_game_over=is_over,
            next_round=next_round_index,
        )

    # ------------------------------------------------------------------
    #  LLM 调用
    # ------------------------------------------------------------------

    def _classify_with_llm(self, player_text: str) -> str | None:
        """调用 LLM 做策略分类。失败返回 None。"""
        try:
            resp = self._client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": STRATEGY_CLASSIFY_SYSTEM},
                    {"role": "user",   "content": f"玩家发言：{player_text}"},
                ],
                temperature=0.1,
                max_tokens=16,
            )
            raw = resp.choices[0].message.content or ""
            return self._clean_strategy_label(raw)
        except Exception:
            return None

    def _generate_hr_reply(self, strategy: str, player_text: str, state: SessionState) -> str:
        """调用 LLM 生成 HR 回复。失败回退到静态兜底。"""
        user_prompt = self._build_hr_prompt(strategy, player_text, state)
        try:
            resp = self._client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": HR_REPLY_SYSTEM},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=200,
            )
            reply = (resp.choices[0].message.content or "").strip()
            if reply:
                return reply
        except Exception:
            pass
        return self._FALLBACK_REPLIES.get(strategy, self._FALLBACK_REPLIES["probe"])

    # ------------------------------------------------------------------
    #  内部工具方法
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_strategy_label(raw: str) -> str | None:
        """从 LLM 原始输出中提取有效策略标签，支持模糊匹配。"""
        valid = {"strong_push", "probe", "concede", "counter_pressure", "legal_quote", "trap_detect"}
        text = raw.strip().lower()
        for label in valid:
            if label in text:
                return label
        fuzzy: dict[str, str] = {
            "strong": "strong_push", "push": "strong_push",
            "probe": "probe",
            "concede": "concede",
            "counter": "counter_pressure", "pressure": "counter_pressure",
            "legal": "legal_quote", "quote": "legal_quote",
            "trap": "trap_detect", "detect": "trap_detect",
        }
        for keyword, label in fuzzy.items():
            if keyword in text:
                return label
        return None

    @staticmethod
    def _build_hr_prompt(strategy: str, player_text: str, state: SessionState) -> str:
        patience_desc = "友好" if state.hr_patience > 60 else ("一般" if state.hr_patience > 30 else "不耐烦")
        strategy_cn = {
            "strong_push": "强势施压",
            "probe": "迂回试探",
            "concede": "配合妥协",
            "counter_pressure": "反问逼牌",
            "legal_quote": "法条引用",
            "trap_detect": "识破陷阱",
        }.get(strategy, "未知")
        return (
            f"当前状态：第 {state.round_index} / {state.max_round} 轮，"
            f"耐心值 {state.hr_patience}/100（{patience_desc}），"
            f"信息暴露度 {state.info_exposure}/100。\n"
            f"当前报价：15K/月，14薪。\n"
            f"玩家策略：{strategy_cn}\n"
            f"玩家发言：{player_text}\n\n"
            f"请以张敏的身份生成HR的回复："
        )

    def _compute_delta(self, strategy: str, state: SessionState) -> TurnDelta:
        """计算本回合状态增量，后期回合波动放大。"""
        base_p, base_e, base_t = self.BASE_DELTA.get(strategy, self.BASE_DELTA["probe"])
        scale = 1.0 + (state.round_index - 1) * 0.25
        return TurnDelta(
            hr_patience=int(base_p * scale),
            info_exposure=int(base_e * scale),
            trap_count=base_t,
        )
