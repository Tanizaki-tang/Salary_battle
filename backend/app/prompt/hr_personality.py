from __future__ import annotations

import re
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Final

DEFAULT_PERSONALITY_ID: Final[str] = "hr_smiling_tiger"
PERSONALITIES_DIR = Path(__file__).resolve().parents[3] / "hr-personalities"

_QUOTE_PATTERN = re.compile(r"「([^」]+)」")


@dataclass(frozen=True, slots=True)
class HrPersonalityMeta:
    personality_id: str
    name: str
    tagline: str
    emoji: str
    filename: str
    patience_bias: int


_PERSONALITY_REGISTRY: dict[str, HrPersonalityMeta] = {
    "hr_newbie": HrPersonalityMeta(
        personality_id="hr_newbie",
        name="菜鸟新人",
        tagline="紧张没底气，容易说漏信息",
        emoji="🐣",
        filename="personality-newbie.md",
        patience_bias=8,
    ),
    "hr_robot": HrPersonalityMeta(
        personality_id="hr_robot",
        name="冷漠流程型",
        tagline="按系统流程办事，几乎无情绪波动",
        emoji="🤖",
        filename="personality-robot.md",
        patience_bias=5,
    ),
    "hr_aggressive": HrPersonalityMeta(
        personality_id="hr_aggressive",
        name="强势压价型",
        tagline="开门见山压价，耐心极低",
        emoji="💪",
        filename="personality-aggressive.md",
        patience_bias=-18,
    ),
    "hr_honest": HrPersonalityMeta(
        personality_id="hr_honest",
        name="老实人型",
        tagline="真诚坦率，容易被说服",
        emoji="😇",
        filename="personality-honest.md",
        patience_bias=6,
    ),
    "hr_smiling_tiger": HrPersonalityMeta(
        personality_id="hr_smiling_tiger",
        name="笑面虎型",
        tagline="表面热情，话术圆滑",
        emoji="😊",
        filename="personality-smiling-tiger.md",
        patience_bias=-2,
    ),
}


def resolve_personality_id(personality_id: str | None) -> str:
    pid = (personality_id or "").strip()
    if pid in _PERSONALITY_REGISTRY:
        return pid
    return DEFAULT_PERSONALITY_ID


def list_personalities() -> list[dict[str, str | int]]:
    return [
        {
            "personality_id": meta.personality_id,
            "name": meta.name,
            "tagline": meta.tagline,
            "emoji": meta.emoji,
            "patience_bias": meta.patience_bias,
        }
        for meta in _PERSONALITY_REGISTRY.values()
    ]


def get_personality_meta(personality_id: str | None) -> HrPersonalityMeta:
    return _PERSONALITY_REGISTRY[resolve_personality_id(personality_id)]


def apply_personality_patience(base_patience: int, personality_id: str | None) -> int:
    meta = get_personality_meta(personality_id)
    return max(0, min(100, base_patience + meta.patience_bias))


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _extract_quote_examples(md_text: str) -> list[str]:
    """从 MD 中提取所有「...」单句话术示例。"""
    quotes: list[str] = []
    for line in md_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-") or "「" not in stripped:
            continue
        for match in _QUOTE_PATTERN.finditer(stripped):
            quotes.append(f"「{match.group(1)}」")
    return _dedupe_preserve_order(quotes)


def _extract_dialogue_examples(md_text: str) -> list[str]:
    """从情绪响应矩阵等章节提取「玩家 / HR」完整对话块。"""
    lines = md_text.splitlines()
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("> 玩家：") or stripped.startswith("> HR："):
            block_lines: list[str] = []
            while i < len(lines):
                current = lines[i].strip()
                if not current.startswith(">"):
                    break
                block_lines.append(current[1:].strip())
                i += 1
            if len(block_lines) >= 2:
                blocks.append("\n".join(block_lines))
            continue
        i += 1
    return blocks


def _build_few_shot_section(md_text: str) -> str:
    quote_examples = _extract_quote_examples(md_text)
    dialogue_examples = _extract_dialogue_examples(md_text)
    if not quote_examples and not dialogue_examples:
        return ""

    parts = [
        "## 话术示例库（Few-Shot — 生成 hr_reply 时必须参考）",
        "以下示例从人格文档提取。请化用其语气、措辞与施压/共情节奏；可调整具体数字与细节，但不可偏离该人格说话方式。",
    ]
    if quote_examples:
        parts.append("")
        parts.append("### 单句话术参考")
        parts.extend(f"{idx}. {quote}" for idx, quote in enumerate(quote_examples, start=1))
    if dialogue_examples:
        parts.append("")
        parts.append("### 完整对话参考")
        for idx, block in enumerate(dialogue_examples, start=1):
            parts.append(f"**示例 {idx}**")
            parts.append(block)
            parts.append("")
    return "\n".join(parts).strip()


def get_personality_prompt(personality_id: str | None) -> str:
    meta = get_personality_meta(personality_id)
    prompt_file = PERSONALITIES_DIR / meta.filename
    if prompt_file.exists():
        body = prompt_file.read_text(encoding="utf-8").strip()
    else:
        body = f"你是{meta.name}型HR。{meta.tagline}。请严格保持该人格的沟通风格与决策倾向。"
    few_shot = _build_few_shot_section(body) if prompt_file.exists() else ""
    sections = [
        "## HR人格设定（必须严格遵守）",
        f"- 人格ID: {meta.personality_id}",
        f"- 人格名称: {meta.emoji} {meta.name}",
        f"- 一句话印象: {meta.tagline}",
    ]
    if few_shot:
        sections.extend(["", few_shot])
    sections.extend(["", body, ""])
    sections.append(
        "在生成 hr_reply 时，必须完全体现上述人格的语气、话术习惯与情绪响应；"
        "优先参考「话术示例库」中的单句与对话风格，不可跳出人格。"
    )
    return "\n".join(sections)


def pick_random_personality_id() -> str:
    return random.choice(list(_PERSONALITY_REGISTRY.keys()))


def _strip_wrapping_quotes(text: str) -> str:
    """去掉人格文档示例话术外层的引号/书名号。"""
    return text.strip().strip("「」『』“”\"'")


def build_personality_opening(
    *,
    user_name: str,
    personality_id: str | None,
    scene_opening_line: str,
    salary_offer: float,
) -> str:
    meta = get_personality_meta(personality_id)
    prompt_file = PERSONALITIES_DIR / meta.filename
    body = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""

    offer_str = str(int(salary_offer)) if float(salary_offer).is_integer() else str(salary_offer)
    offer_token = f"{offer_str}K"

    candidates: list[str] = []
    in_opening = False
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            if in_opening and candidates:
                break
            continue
        if line.startswith("#"):
            if in_opening and candidates:
                break
            in_opening = "开场风格" in line
            continue
        if in_opening and line.startswith("-"):
            text = _strip_wrapping_quotes(line.lstrip("-").strip())
            if text:
                candidates.append(text)

    opening = random.choice(candidates) if candidates else ""
    if opening:
        opening = opening.replace("月薪X", f"月薪{offer_token}").replace("薪资这块是X", f"薪资这块是{offer_token}")
        opening = opening.replace("X——", f"{offer_token}——").replace("X，", f"{offer_token}，").replace("X", offer_token)
        opening = _strip_wrapping_quotes(opening)
    elif scene_opening_line.strip():
        opening = _strip_wrapping_quotes(scene_opening_line)
        opening = opening.replace("{salary_offer}", offer_token).replace("{user_name}", user_name)
    else:
        opening = f"感谢你来面试！我们这边初步给到月薪{offer_token}，你这边怎么看？"

    return opening
