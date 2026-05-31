from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from app.api.card_game_routes import router as card_game_router
from app.api.session_routes import router as session_router
from app.api.voice_battle_routes import router as voice_battle_router


app = FastAPI(title="Salary Battle API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
    ],
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
