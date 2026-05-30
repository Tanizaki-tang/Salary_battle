"""
场景加载器 — 从 scenario .md 文件提取 HR System Prompt，实现动态场景切换。
"""
from __future__ import annotations

import re
from pathlib import Path


# 默认场景文件路径
DEFAULT_SCENARIO = Path(__file__).resolve().parents[4] / "scenario-tech-startup(1).md"


def load_hr_system_prompt(scenario_path: str | Path | None = None) -> str:
    """从场景 .md 文件中提取 HR System Prompt。

    加载的章节（用于注入 LLM）：
      - 一、HR 人设与行为准则
      - 二、场景设定（薪资锚点、工时社保）
      - 三、玩家意图分类
      - 四、陷阱机制
      - 五、对话流程与数值管理
      - 六、回复生成指南（话术范例+禁止事项）
      - 九、完整示例对话（Few-Shot）

    跳过的章节（代码负责）：
      - 七、终局结算
      - 八、开场白
      - 十、开发者备注
    """
    path = Path(scenario_path) if scenario_path else DEFAULT_SCENARIO
    if not path.exists():
        raise FileNotFoundError(f"场景文件不存在: {path}")

    content = path.read_text(encoding="utf-8")

    # 按 "## " 分割章节
    sections = _split_sections(content)

    # 需要加载的章节关键词
    include_keywords = [
        "HR 人设", "HR人设",
        "场景设定",
        "玩家意图分类", "意图分类",
        "陷阱机制",
        "对话流程", "数值管理",
        "回复生成指南", "回复指南",
        "完整示例对话", "示例对话",
    ]

    # 明确跳过的章节关键词
    skip_keywords = [
        "终局结算",
        "开场白",
        "开发者备注",
    ]

    prompt_parts: list[str] = []

    for title, body in sections:
        # 检查是否应跳过
        if any(kw in title for kw in skip_keywords):
            continue
        # 检查是否应包含
        if any(kw in title for kw in include_keywords):
            # 清理章节内容：去掉代码块标记但保留内容
            clean_body = _clean_section_body(body)
            prompt_parts.append(f"## {title}\n\n{clean_body}")

    if not prompt_parts:
        raise ValueError("未能从场景文件中提取到任何有效章节")

    # 加一个总指令头
    header = (
        "你是薪资谈判游戏中的HR。请严格按照以下设定进行角色扮演。\n"
        "本文档定义规则和边界，不定义逐字剧本。"
        "你在每个对话回合根据玩家输入、当前状态和自身人设即兴生成回复。\n\n"
    )

    return header + "\n\n".join(prompt_parts)


def load_opening_template(scenario_path: str | Path | None = None) -> str:
    """从场景文件第八节提取开场白模板。"""
    path = Path(scenario_path) if scenario_path else DEFAULT_SCENARIO
    if not path.exists():
        return "你好，我们这边给你的总包是 12k*14，你怎么看？"

    content = path.read_text(encoding="utf-8")
    sections = _split_sections(content)

    for title, body in sections:
        if "开场白" in title:
            # 提取 > 引用的开场白内容
            match = re.search(r'>\s*👩‍💼\s*\*{0,2}张敏\*{0,2}[：:]\s*(.+?)(?:\n|$)', body)
            if match:
                return match.group(1).strip()
            # 如果没有找到特定格式，尝试找任意引用行
            match = re.search(r'>\s*(.+?offer.+?)(?:\n|$)', body)
            if match:
                return match.group(1).strip()

    return "你好！感谢你参加了我们的面试，团队对你印象很好。我们想给你发一个后端开发的offer：月薪15K，14薪。公司现在A轮，发展很快，你觉得怎么样？"


def _split_sections(content: str) -> list[tuple[str, str]]:
    """将 Markdown 按 ## 标题分割为 (标题, 正文) 列表。"""
    # 去掉文件开头的元信息（# 一级标题和引用块）
    # 找到第一个 ## 的位置
    first_h2 = content.find("\n## ")
    if first_h2 == -1:
        return [("全文", content)]
    content = content[first_h2:]

    # 按 ## 分割
    parts = re.split(r"\n(?=## )", content)
    result: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        lines = part.split("\n", 1)
        title = lines[0].replace("## ", "").strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        result.append((title, body))
    return result


def _clean_section_body(body: str) -> str:
    """清理章节正文：保留表格和引用，去掉过多的空行。"""
    # 去掉代码块标记（``` 和 ```），但保留内容
    body = re.sub(r"^```\w*\n?", "", body, flags=re.MULTILINE)
    body = re.sub(r"\n```$", "", body)
    # 压缩连续空行为最多两行
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()
