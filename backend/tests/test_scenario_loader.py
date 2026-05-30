from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from unittest.mock import patch

from app.prompt.character_prompt import GM_SCENE_IDS, _SCENE_PROMPTS, build_system_prompt, get_scene_prompt
from app.prompt.scenario_loader import DEFAULT_SCENARIO, load_hr_system_prompt, load_opening_template


def test_default_scenario_file_exists() -> None:
    assert DEFAULT_SCENARIO.exists(), f"missing GM file: {DEFAULT_SCENARIO}"


def test_load_hr_system_prompt_contains_core_sections() -> None:
    prompt = load_hr_system_prompt()
    assert len(prompt) > 500
    assert "张敏" in prompt
    assert "陷阱" in prompt
    assert "回复生成指南" in prompt or "话术" in prompt


def test_load_opening_template_non_empty() -> None:
    opening = load_opening_template()
    assert len(opening.strip()) > 10


def test_scene_001_uses_gm_prompt() -> None:
    gm_prompt = get_scene_prompt("scene_001")
    short_prompt = _SCENE_PROMPTS["scene_001"]
    assert len(gm_prompt) > len(short_prompt) * 3
    assert "张敏" in gm_prompt


def test_build_system_prompt_skips_traps_for_gm_scene() -> None:
    marker = "<<<TRAPS_MARKER>>>"
    with patch("app.prompt.character_prompt.get_traps_prompt", return_value=marker):
        prompt = build_system_prompt("BASE_RULES", "scene_001", "hr_newbie")
        assert marker not in prompt
        assert "BASE_RULES" in prompt
        assert "张敏" in prompt

        other = build_system_prompt("BASE_RULES", "scene_002", None)
        assert marker in other


def test_build_system_prompt_keeps_traps_for_other_scenes() -> None:
    prompt = build_system_prompt("BASE_RULES", "scene_002", None)
    assert "陷阱 A" in prompt


def test_gm_scene_ids_include_aliases() -> None:
    assert "scene_001" in GM_SCENE_IDS
    assert "scenario_001" in GM_SCENE_IDS


if __name__ == "__main__":
    tests = [
        test_default_scenario_file_exists,
        test_load_hr_system_prompt_contains_core_sections,
        test_load_opening_template_non_empty,
        test_scene_001_uses_gm_prompt,
        test_build_system_prompt_skips_traps_for_gm_scene,
        test_build_system_prompt_keeps_traps_for_other_scenes,
        test_gm_scene_ids_include_aliases,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}")
    if failed:
        raise SystemExit(1)
    print(f"All {len(tests)} tests passed.")
