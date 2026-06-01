from pathlib import Path
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.api.card_game_routes import router as card_game_router
from app.api.session_routes import router as session_router
from app.api.voice_battle_routes import router as voice_battle_router
from app.db import init_db


def _cors_origins() -> list[str]:
    raw = (os.getenv("CORS_ALLOW_ORIGINS") or "").strip()
    if raw:
        return [item.strip() for item in raw.split(",") if item.strip()]
    return [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ]


def _cors_origin_regex() -> str | None:
    raw = (os.getenv("CORS_ALLOW_ORIGIN_REGEX") or "").strip()
    return raw or None


app = FastAPI(title="Salary Battle API", version="0.1.0")


@app.on_event("startup")
def startup() -> None:
    init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_origin_regex=_cors_origin_regex(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(session_router)
app.include_router(card_game_router)
app.include_router(voice_battle_router)

resources_dir = Path(__file__).resolve().parents[2] / "resources"
if resources_dir.exists():
    app.mount("/resources", StaticFiles(directory=str(resources_dir)), name="resources")
