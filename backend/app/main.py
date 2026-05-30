import sys
from pathlib import Path

# 确保 backend 目录在 sys.path 中，支持直接 python main.py 启动
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI
import uvicorn


from app.api.session_routes import router as session_router


app = FastAPI(title="Salary Battle API", version="0.1.0")
app.include_router(session_router)

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
