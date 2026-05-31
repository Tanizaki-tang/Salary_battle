from __future__ import annotations

import re

# 内部状态：元/月；对玩家口语：K/月（1K = 1000 元）
_SALARY_K_SUFFIX_RE = re.compile(r"(\d{4,})K", re.IGNORECASE)


def yuan_to_k(yuan: int | float) -> float:
    return round(float(yuan) / 1000.0, 1)


def format_salary_k(yuan: int | float) -> str:
    """13000 -> '13K'，15500 -> '15.5K'"""
    k = yuan_to_k(yuan)
    if abs(k - round(k)) < 1e-6:
        return f"{int(round(k))}K"
    return f"{k:.1f}K"


def format_salary_yuan(yuan: int | float) -> str:
    value = int(round(float(yuan)))
    return f"{value:,}元"


def fix_misformatted_salary_k(text: str) -> str:
    """把口语里误写的 13000K 纠正为 13K。"""
    if not text:
        return text

    def repl(match: re.Match[str]) -> str:
        num = int(match.group(1))
        if num >= 1000 and num % 1000 == 0:
            return format_salary_k(num)
        return match.group(0)

    return _SALARY_K_SUFFIX_RE.sub(repl, text)


def apply_opening_placeholders(
    text: str,
    *,
    offer_token: str,
    company_name: str = "灵创科技",
) -> str:
    """替换开场白里的公司与薪资占位符，避免把 XX 公司误替换成 15K15K。"""
    result = text
    company = company_name.strip() or "灵创科技"
    result = result.replace("XX 公司", company)
    result = result.replace("XX公司", company)
    result = result.replace("XX 公司的", f"{company}的")
    result = result.replace("XX公司的", f"{company}的")
    result = result.replace("我是XX", f"我是{company}")

    salary_rules = (
        ("月薪X", f"月薪{offer_token}"),
        ("薪资这块是X", f"薪资这块是{offer_token}"),
        ("offer是X", f"offer是{offer_token}"),
        ("薪资是X", f"薪资是{offer_token}"),
        ("给到X", f"给到{offer_token}"),
        ("X元", f"{offer_token}元"),
        ("X——", f"{offer_token}——"),
        ("X，", f"{offer_token}，"),
        ("X。", f"{offer_token}。"),
    )
    for src, dst in salary_rules:
        result = result.replace(src, dst)

    # 仅替换落单的薪资占位 X，不影响已替换文本
    result = re.sub(r"(?<![X\w])X(?![X\w])", offer_token, result)
    return result


def enrich_negotiation_salary_fields(payload: dict) -> dict:
    """为 LLM 补充可读的 K 制薪资字段，避免把元数字当 K 报出。"""
    yuan = payload.get("current_salary_offer")
    if isinstance(yuan, (int, float)):
        payload = {**payload}
        payload["current_salary_offer_k"] = yuan_to_k(yuan)
        payload["current_salary_offer_display"] = format_salary_k(yuan)
        anchor = payload.get("salary_anchor")
        if isinstance(anchor, dict):
            enriched = dict(anchor)
            for key in ("legal_floor", "market_fair", "ideal_target", "hr_initial_offer"):
                if key in enriched and isinstance(enriched[key], (int, float)):
                    enriched[f"{key}_k"] = yuan_to_k(enriched[key])
            payload["salary_anchor"] = enriched
    return payload
