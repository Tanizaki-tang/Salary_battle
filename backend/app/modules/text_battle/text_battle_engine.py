from __future__ import annotations

from openai import OpenAI

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, LLM_TIMEOUT
from app.contracts.text_battle_contract import TextBattleContract
from app.shared_types.game_types import SessionState, TextTurnPayload, TurnDelta, TurnResult


# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

STRATEGY_CLASSIFY_SYSTEM = """你是一个薪资谈判游戏的策略分类器。根据玩家发言，判断其策略类型。

策略定义：
- strong_push: 强硬拒绝、坚持高要求、表达不满、直接施压
- probe: 试探询问、获取信息、了解细节、确认条款
- concede: 让步妥协、表示理解配合、接受条件、缓和气氛
- counter_pressure: 反向施压、提及竞争offer、强调自身价值、拿市场行情说事

你必须且只能回复以下四个英文标签之一：strong_push, probe, concede, counter_pressure
不要回复中文，不要回复任何其他内容。"""

HR_REPLY_SYSTEM = """你是薪资谈判游戏中的HR。根据当前谈判局势，生成符合人设的回复。

## 你的人设
- 专业、有底线，但愿意推动沟通
- 你不是来吵架的，是来寻找双方都能接受的方案
- 你有薪资弹性空间，但不会无底线让步

## 回复要求
- 语气与耐心值对应：耐心>60时友好开放，耐心30-60时务实中性，耐心<30时直接强硬
- 回复紧扣玩家的发言内容，不要跑题
- 控制在80字以内
- 只返回回复文本，不要加任何前缀说明"""


class TextBattleEngine(TextBattleContract):
    """文本谈判引擎 — 调用 DeepSeek LLM 进行策略分类和 HR 回复生成。"""

    # ---- 策略 → delta 映射（规则驱动） ----
    BASE_DELTA: dict[str, tuple[int, int, int]] = {
        "strong_push":      (-10, -3, 0),
        "probe":            (-3,  -8, 0),
        "concede":          (8,    5, 0),
        "counter_pressure": (-6,  -6, 1),
    }

    # ---- LLM 不可用时的兜底回复 ----
    _FALLBACK_REPLIES: dict[str, str] = {
        "strong_push":      "我理解你的期望，但预算确实有一定限制，我们尽量在范围内协商。",
        "probe":            "你可以具体说说你想了解的方向，我尽量给你解释清楚。",
        "concede":          "好的，感谢你的理解，我们继续往下推进吧。",
        "counter_pressure": "市场竞争的情况我了解，不过我们也有自己的优势可以综合考虑。",
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
        """调用 LLM 生成 HR 开场白，每次随机选一种风格。失败返回兜底。"""
        import random

        styles = [
            "你是HR，用轻松自然的语气开场，打个招呼后把话题引到薪资上。40字以内。",
            "你是HR，用正式专业的语气开场，简要介绍薪资结构后询问对方期望。40字以内。",
            "你是HR，直接开门见山，不寒暄，单刀直入谈薪资数字。40字以内。",
            "你是HR，先夸一下候选人的能力，再顺势引出薪资话题。40字以内。",
            "你是HR，用比较坦诚的语气，说明公司预算有限但愿意协商。40字以内。",
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
        return "你好，我们这边给你的总包是 12k*14，你怎么看？"

    # ------------------------------------------------------------------
    #  Contract 实现
    # ------------------------------------------------------------------

    def parse_strategy(self, text_payload: TextTurnPayload) -> str:
        """解析玩家策略。

        优先级：payload.strategy 显式值 > LLM 分类 > 兜底 probe。
        """
        # 1) 显式策略：直接信任前端传值
        if text_payload.strategy:
            return text_payload.strategy

        # 2) 有自由文本：交给 LLM 分类
        if text_payload.player_text:
            strategy = self._classify_with_llm(text_payload.player_text)
            if strategy:
                return strategy

        # 3) 兜底
        return "probe"

    def run_text_turn(
        self, session_state: SessionState, text_payload: TextTurnPayload) -> TurnResult:
        """执行一个文本回合（修正了游戏结束条件与回合计数）。"""
        # 1) 解析出最终策略标签
        strategy = self.parse_strategy(text_payload)
        
        # 2) 生成大模型/兜底 HR 回复
        hr_reply = self._generate_hr_reply(strategy, text_payload.player_text or "", session_state)
        
        # 3) 计算当前回合的增量变化
        delta = self._compute_delta(strategy, session_state)
        
        # 4) 计算这一轮扣减/增加后，临时的实际分值
        # 接口设计中 delta.hr_patience 是负数 (例如 -10)，所以用加法
        current_calculated_patience = session_state.hr_patience + delta.hr_patience
        
        # 5) 综合判定游戏是否结束
        # 结束条件 1: 耐心值耗尽（小于等于 0）
        # 结束条件 2: 当前回合已经达到了最大回合上限
        is_over = (current_calculated_patience <= 0) or (session_state.round_index >= session_state.max_round)
        
        # 6) 计算下一轮的数字（不需要 min 强行封顶，让其自然 +1，依靠 is_game_over 控制流转）
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
        valid = {"strong_push", "probe", "concede", "counter_pressure"}
        text = raw.strip().lower()
        # 精确匹配
        for label in valid:
            if label in text:
                return label
        # 模糊匹配：LLM 可能只返回部分词如 "strong", "counter" 等
        fuzzy: dict[str, str] = {
            "strong": "strong_push",
            "push": "strong_push",
            "probe": "probe",
            "concede": "concede",
            "counter": "counter_pressure",
            "pressure": "counter_pressure",
        }
        for keyword, label in fuzzy.items():
            if keyword in text:
                return label
        return None

    @staticmethod
    def _build_hr_prompt(strategy: str, player_text: str, state: SessionState) -> str:
        patience_desc = "友好" if state.hr_patience > 60 else ("一般" if state.hr_patience > 30 else "不耐烦")
        strategy_cn = {
            "strong_push": "强硬施压",
            "probe": "试探询问",
            "concede": "让步妥协",
            "counter_pressure": "反向施压",
        }.get(strategy, "未知")
        return (
            f"当前状态：第 {state.round_index} / {state.max_round} 轮，"
            f"耐心值 {state.hr_patience}/100（{patience_desc}），"
            f"信息暴露度 {state.info_exposure}/100。\n"
            f"玩家策略：{strategy_cn}\n"
            f"玩家发言：{player_text}\n\n"
            f"请生成HR的回复："
        )

    def _compute_delta(self, strategy: str, state: SessionState) -> TurnDelta:
        """计算本回合状态增量，后期回合波动放大。"""
        base_p, base_e, base_t = self.BASE_DELTA.get(strategy, self.BASE_DELTA["probe"])
        scale = 1.0 + (state.round_index - 1) * 0.25  # round1=1.0, round5=2.0
        return TurnDelta(
            hr_patience=int(base_p * scale),
            info_exposure=int(base_e * scale),
            trap_count=base_t,
        )
