from __future__ import annotations

import re

# 日常 IM/谈薪聊天口径（中文按字符计）
HR_REPLY_MAX_CHARS = 80
HR_REPLY_HARD_MAX_CHARS = 120
HR_QUESTION_MAX_CHARS = 60
PLAYER_REPLY_MAX_CHARS = 40

DIALOGUE_LENGTH_RULES = """## 对话字数约束（必须严格遵守）
- 场景是 Boss 直聘式即时聊天，不是邮件或报告；用口语短句，像真人打字。
- HR 的 hr_reply：通常 1~2 句，总字数不超过 80 字；绝不超过 120 字。
- HR 提问/情境：1~2 句，不超过 60 字。
- 玩家回复（若有）：每条单句，不超过 40 字。
- 禁止：长段落、分点列举、「首先/其次/综上」、Markdown、官方腔套话。"""

HIRE_OUTCOME_CONSISTENCY_RULES = """## 录用/未录用结果一致性（必须严格遵守）
- 游戏结算页会展示「录用」或「未录用」。你的 hr_reply、should_end、reason 必须与当前谈判走向一致，不得自相矛盾。
- **已明确表达录用意愿时，禁止输出未录用结果**：
  - 若本轮或 history.recent_hr_replies 中已出现 offer、决定录用、欢迎加入、发 offer、薪资已定、可以入职、通过面试 等录用意愿，
  - 则 hr_reply **不得**出现：未录用、不予录用、不招、offer 收回、无缘、不合适、没通过、谈崩 等否定录用表述；
  - 此时 should_end=true 仅表示**进入录用结算**（如玩家接受 offer、双方谈妥条件），reason 不得描述为未录用或谈判破裂。
- **未录用/谈崩仅当**：HR 明确撤回 offer、拒绝继续沟通，或 HR 耐心耗尽且不再给出录用可能时，才可使用否定录用话术并结束对局。
- 开场已发 offer 的场景，默认处于「已有录用意向、协商条件」阶段；后续是谈薪与条款，不是重新决定是否录用——除非出现上述谈崩条件。
- **禁止同轮或连续轮次**既承诺录用又否定录用（例如先说「决定录用你」再说「未录用」）。"""

HR_REPLY_FIELD_HINT = f"string，口语短句，1~2句，≤{HR_REPLY_MAX_CHARS}字"
HR_QUESTION_FIELD_HINT = f"string，口语短句，1~2句，≤{HR_QUESTION_MAX_CHARS}字"
PLAYER_REPLY_FIELD_HINT = f"string，单句口语，≤{PLAYER_REPLY_MAX_CHARS}字"


def clamp_chat_text(text: str, max_chars: int, *, hard_max: int | None = None) -> str:
    """截断过长模型输出，尽量在句末标点处断开。"""
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    if not cleaned:
        return cleaned
    limit = hard_max if hard_max is not None else max_chars
    if len(cleaned) <= limit:
        return cleaned
    chunk = cleaned[:limit]
    for sep in ("。", "！", "？", "；", "，", " ", "…"):
        idx = chunk.rfind(sep)
        if idx >= max(12, limit // 3):
            return chunk[: idx + 1].strip()
    return chunk.rstrip() + "…"


def clamp_hr_reply(text: str) -> str:
    return clamp_chat_text(text, HR_REPLY_MAX_CHARS, hard_max=HR_REPLY_HARD_MAX_CHARS)


def clamp_hr_question(text: str) -> str:
    return clamp_chat_text(text, HR_QUESTION_MAX_CHARS, hard_max=HR_QUESTION_MAX_CHARS + 20)


def clamp_player_reply(text: str) -> str:
    return clamp_chat_text(text, PLAYER_REPLY_MAX_CHARS, hard_max=PLAYER_REPLY_MAX_CHARS + 10)
