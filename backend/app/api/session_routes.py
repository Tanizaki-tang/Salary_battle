from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.modules.flow_controller.orchestrator import GameFlowOrchestrator
from app.prompt.hr_personality import (
    apply_personality_patience,
    build_personality_opening,
    get_personality_meta,
    list_personalities,
    pick_random_personality_id,
    resolve_personality_id,
)
from app.repositories.scene_repository import load_scene, resolve_scene_id
from app.service.llm_service import llm_latency_enabled
from app.shared_types.game_types import ApiResponse, ConversationMessage, SessionState, TextTurnPayload


router = APIRouter(prefix="/api/v1", tags=["game"])
orchestrator = GameFlowOrchestrator()
SESSIONS: dict[str, SessionState] = {}
logger = logging.getLogger(__name__)


@router.get("/health")
def health() -> ApiResponse:
    return ApiResponse(data={"status": "healthy", "service": "salary-battle-api", "version": "v1.2"})


@router.get("/hr-personalities")
def get_hr_personalities() -> ApiResponse:
    return ApiResponse(data={"personalities": list_personalities()})


@router.post("/sessions")
def create_session(payload: dict) -> ApiResponse:
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    user_name = (payload.get("user_name") or "").strip() or "候选人"
    scene_id = resolve_scene_id(scene_id=payload.get("scene_id"), role_id=payload.get("role_id"))
    role_id = payload.get("role_id") or "role_backend"
    raw_personality = payload.get("hr_personality_id")
    if raw_personality is None or str(raw_personality).strip().lower() in {"", "random"}:
        hr_personality_id = pick_random_personality_id()
    else:
        hr_personality_id = resolve_personality_id(str(raw_personality))
    personality_meta = get_personality_meta(hr_personality_id)
    scene_context = load_scene(scene_id)
    initial = scene_context.initial_state
    opening = build_personality_opening(
        user_name=user_name,
        personality_id=hr_personality_id,
        scene_opening_line=scene_context.opening_line,
        salary_offer=scene_context.salary_anchor.hr_initial_offer,
    )
    opening_with_name = opening if opening.startswith(f"{user_name}，") else f"{user_name}，{opening}"
    session = SessionState(
        session_id=f"sess_{uuid4().hex[:8]}",
        user_id=user_id,
        user_name=user_name,
        hr_personality_id=hr_personality_id,
        role_id=role_id,
        scene_id=scene_id,
        max_round=initial.max_round,
        hr_patience=apply_personality_patience(initial.hr_patience, hr_personality_id),
        info_exposure=initial.info_exposure,
        trap_count=initial.trap_count,
        current_salary_offer=scene_context.salary_anchor.hr_initial_offer,
        conversation_history=[
            ConversationMessage(
                role="hr",
                content=opening_with_name,
                round_index=0,
            )
        ],
        scene_context=scene_context,
    )
    SESSIONS[session.session_id] = session
    return ApiResponse(
        data={
            "session": session.model_dump(),
            "hr_opening": opening_with_name,
            "scene_meta": scene_context.meta.model_dump(),
            "hr_personality_meta": {
                "personality_id": personality_meta.personality_id,
                "name": personality_meta.name,
                "tagline": personality_meta.tagline,
                "emoji": personality_meta.emoji,
            },
        }
    )


@router.post("/sessions/{session_id}/text-turn")
def text_turn(session_id: str, payload: TextTurnPayload) -> ApiResponse:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    started = time.perf_counter()
    next_state, turn_result, flow = orchestrator.run_text_turn(session, payload)
    SESSIONS[session_id] = next_state
    if llm_latency_enabled():
        logger.info(
            "LATENCY_API_TEXT_TURN session_id=%s round=%s total_ms=%.1f",
            session_id,
            session.round_index,
            (time.perf_counter() - started) * 1000,
        )
    return ApiResponse(data={"result": turn_result.model_dump(), "session": next_state.model_dump(), "flow": flow.model_dump()})


@router.post("/sessions/{session_id}/settle")
def settle(session_id: str) -> ApiResponse:
    session = SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    settle_result, persist_result = orchestrator.settle_and_persist(session)
    session.status = "settled"
    SESSIONS[session_id] = session
    return ApiResponse(data={"result": settle_result.model_dump(), "persist": persist_result.model_dump()})
