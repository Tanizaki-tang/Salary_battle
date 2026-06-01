from __future__ import annotations

import json
from pathlib import Path

from app.prompt.traps_prompt import get_traps_prompt
from app.repositories.scene_repository import ROLE_TO_SCENE, get_scene_trap_labels, load_scene


def test_generated_scene_specs_exist_and_are_consumed() -> None:
    specs_path = Path(__file__).resolve().parents[1] / "app" / "generated" / "scene_specs.json"
    payload = json.loads(specs_path.read_text(encoding="utf-8"))

    assert payload["generated_from"] == "scene_storyies/*.md"
    assert len(payload["scenes"]) == 3
    assert ROLE_TO_SCENE["role_ops"] == "scene_002"
    assert load_scene("scene_003").meta.scene_name == "大厂管培生"
    assert payload["scenes"][0]["traps"][0]["trap_id"] == "A"


def test_generated_traps_drive_prompt_and_labels() -> None:
    prompt = get_traps_prompt("scene_003")
    trap_labels = get_scene_trap_labels("scene_001")

    assert "总包数字灌水" in prompt
    assert "竞业限制轻描淡写" in prompt
    assert trap_labels["A"] == "谁先报价"
    assert trap_labels["D"] == "五险一金模糊"
