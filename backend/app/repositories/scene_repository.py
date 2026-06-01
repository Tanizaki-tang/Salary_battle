from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.shared_types.game_types import (
    InitialState,
    SceneContext,
    SceneMeta,
    ScoreProfile,
    SalaryAnchor,
    StrategyType,
    TurnDelta,
)

GENERATED_SCENE_SPECS_PATH = Path(__file__).resolve().parents[1] / "generated" / "scene_specs.json"

def _load_generated_scene_specs() -> list[dict[str, Any]]:
    if not GENERATED_SCENE_SPECS_PATH.exists():
        raise FileNotFoundError(
            f"Generated scene specs not found: {GENERATED_SCENE_SPECS_PATH}. "
            "Run `python scripts/build_scene_specs.py` first."
        )
    payload = json.loads(GENERATED_SCENE_SPECS_PATH.read_text(encoding="utf-8"))
    return payload["scenes"]


def _build_scene(spec: dict[str, Any]) -> SceneContext:
    tone_map = {key: value for key, value in spec["tone_map"].items()}
    strategy_delta_map = {
        key: TurnDelta(**value)
        for key, value in spec["strategy_delta_map"].items()
    }
    return SceneContext(
        meta=SceneMeta(
            scene_id=spec["scene_id"],
            scene_name=spec["scene_name"],
            role_hint=spec["role_hint"],
        ),
        opening_line=spec["opening_line"],
        initial_state=InitialState(**spec["initial_state"]),
        salary_anchor=SalaryAnchor(**spec["salary_anchor"]),
        score_profile=ScoreProfile(**spec["score_profile"]),
        tone_map=tone_map,
        strategy_delta_map=strategy_delta_map,
    )


_SCENE_SPECS = _load_generated_scene_specs()
ROLE_TO_SCENE = {spec["role_id"]: spec["scene_id"] for spec in _SCENE_SPECS}
SCENE_REGISTRY: dict[str, SceneContext] = {spec["scene_id"]: _build_scene(spec) for spec in _SCENE_SPECS}
SCENE_SPEC_REGISTRY: dict[str, dict[str, Any]] = {spec["scene_id"]: spec for spec in _SCENE_SPECS}


def resolve_scene_id(scene_id: str | None = None, role_id: str | None = None) -> str:
    if scene_id and scene_id in SCENE_REGISTRY:
        return scene_id
    if role_id and role_id in ROLE_TO_SCENE:
        return ROLE_TO_SCENE[role_id]
    return "scene_001"


def load_scene(scene_id: str) -> SceneContext:
    return SCENE_REGISTRY.get(scene_id, SCENE_REGISTRY["scene_001"])


def get_scene_spec(scene_id: str) -> dict[str, Any]:
    return SCENE_SPEC_REGISTRY.get(scene_id, SCENE_SPEC_REGISTRY["scene_001"])


def get_scene_trap_labels(scene_id: str) -> dict[str, str]:
    spec = get_scene_spec(scene_id)
    return {item["trap_id"]: item["label"] for item in spec.get("traps", [])}
