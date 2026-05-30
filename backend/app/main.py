from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.session_routes import router as session_router


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
