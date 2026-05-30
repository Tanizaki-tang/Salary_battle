from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(slots=True)
class LLMConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout: float = 30.0


def load_config_from_env() -> LLMConfig:
    api_key = os.getenv("BAILIAN_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Environment variable `BAILIAN_API_KEY` is required.")
    base_url = os.getenv("BAILIAN_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    model = os.getenv("BAILIAN_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    timeout = float(os.getenv("BAILIAN_TIMEOUT_SECONDS", "30"))
    return LLMConfig(api_key=api_key, base_url=base_url, model=model, timeout=timeout)
