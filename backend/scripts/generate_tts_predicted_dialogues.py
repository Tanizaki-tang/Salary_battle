from __future__ import annotations

import re
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.prompt.hr_personality import get_personality_meta, list_personalities


QUOTE = re.compile(r"「([^」]+)」")
HR_LINE = re.compile(r"^\s*>\s*HR[：:]\s*(.+?)\s*$")


def _extract_phrases(md_text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for match in QUOTE.finditer(md_text):
        text = match.group(1).strip()
        if text and text not in seen:
            out.append(text)
            seen.add(text)
    for raw in md_text.splitlines():
        m = HR_LINE.match(raw)
        if not m:
            continue
        text = m.group(1).strip()
        if text and text not in seen:
            out.append(text)
            seen.add(text)
    return out


def main() -> int:
    out_path = REPO_ROOT / "develop_documents" / "tts_predicted_dialogues.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    blocks: list[str] = []
    blocks.append("# TTS 预测对话库（由 hr-personalities 自动生成）")
    blocks.append("")
    blocks.append("用于本地 TTS 预热与关键词优先短句。每个 H2 标题必须是 personality_id。")
    blocks.append("")

    personalities = list_personalities()
    for p in personalities:
        pid = str(p.get("personality_id") or "").strip()
        if not pid:
            continue
        meta = get_personality_meta(pid)
        md_file = REPO_ROOT / "hr-personalities" / meta.filename
        if not md_file.exists():
            continue
        body = md_file.read_text(encoding="utf-8")
        phrases = _extract_phrases(body)
        phrases = phrases[:80]
        blocks.append(f"## {pid}")
        blocks.append("")
        blocks.append("- 你好，我是HR张敏。")
        blocks.append("- 我们这边给你的初始offer是月薪一万五，十四薪。")
        blocks.append("- 嗯嗯。")
        blocks.append("- 好的，我明白了。")
        blocks.append("")
        for text in phrases:
            blocks.append(f"- {text}")
        blocks.append("")

    out_path.write_text("\n".join(blocks).strip() + "\n", encoding="utf-8")
    print(f"generated: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

