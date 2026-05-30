from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.modules.card_game.card_dialogue_agent import CardDialogueAgent
from app.modules.card_game.card_engine import CardGameEngine
from app.prompt.hr_personality import get_personality_meta, pick_random_personality_id, resolve_personality_id
from app.shared_types.card_game_types import CardGameState, CardTurnPayload
from app.shared_types.game_types import ApiResponse

router = APIRouter(prefix="/api/v1/card-game", tags=["card-game"])
dialogue_agent = CardDialogueAgent()
engine = CardGameEngine(dialogue_agent=dialogue_agent)
SESSIONS: dict[str, CardGameState] = {}


@router.post("/sessions")
def create_card_session(payload: dict) -> ApiResponse:
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    user_name = (payload.get("user_name") or "").strip() or "候选人"
    raw_personality = payload.get("hr_personality_id")
    if raw_personality is None or str(raw_personality).strip().lower() in {"", "random"}:
        hr_personality_id = pick_random_personality_id()
    else:
        hr_personality_id = resolve_personality_id(str(raw_personality))
    personality_meta = get_personality_meta(hr_personality_id)
    session_id = f"card_{uuid4().hex[:8]}"
    state = engine.create_initial_state(session_id, user_id, user_name, hr_personality_id)
    SESSIONS[session_id] = state
    return ApiResponse(
        data={
            "session": state.model_dump(),
            "hr_personality_meta": {
                "personality_id": personality_meta.personality_id,
                "name": personality_meta.name,
                "tagline": personality_meta.tagline,
                "emoji": personality_meta.emoji,
            },
        }
    )


@router.get("/sessions/{session_id}")
def get_card_session(session_id: str) -> ApiResponse:
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="session not found")
    return ApiResponse(data={"session": state.model_dump()})


@router.post("/sessions/{session_id}/turn")
def card_turn(session_id: str, payload: CardTurnPayload) -> ApiResponse:
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="session not found")
    try:
        next_state, result = engine.play_turn(state, payload.strategy, payload.player_text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    SESSIONS[session_id] = next_state
    return ApiResponse(data={"result": result.model_dump(), "session": next_state.model_dump()})


@router.post("/sessions/{session_id}/accept")
def accept_offer(session_id: str) -> ApiResponse:
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="session not found")
    try:
        next_state, outcome, reason = engine.accept_offer(state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    SESSIONS[session_id] = next_state
    return ApiResponse(
        data={
            "session": next_state.model_dump(),
            "outcome": outcome,
            "reason": reason,
        }
    )


@router.post("/sessions/{session_id}/settle")
def settle_card_game(session_id: str) -> ApiResponse:
    state = SESSIONS.get(session_id)
    if not state:
        raise HTTPException(status_code=404, detail="session not found")
    if state.status == "ongoing":
        state = state.model_copy(update={"status": "forced_settle", "outcome": "forced_deal"})
        SESSIONS[session_id] = state
    result = engine.settle(state)
    SESSIONS[session_id] = state.model_copy(update={"status": "settled"})
    return ApiResponse(data={"result": result.model_dump(), "session": SESSIONS[session_id].model_dump()})
