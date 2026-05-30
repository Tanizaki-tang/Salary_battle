from fastapi import FastAPI

from app.api.session_routes import router as session_router


app = FastAPI(title="Salary Battle API", version="0.1.0")
app.include_router(session_router)
