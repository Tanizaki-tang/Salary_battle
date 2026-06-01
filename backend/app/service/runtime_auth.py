from __future__ import annotations

import hmac
import os
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Header, HTTPException

DEV_UNLOCK_PASSWORD_ENV = "DEV_UNLOCK_PASSWORD"
DEFAULT_DEV_UNLOCK_PASSWORD = "20260531"


@dataclass(slots=True)
class RuntimeAuth:
    source: Literal["user", "project"]
    user_api_key: str = ""


_runtime_auth_var: ContextVar[RuntimeAuth | None] = ContextVar("runtime_auth", default=None)


def get_runtime_auth() -> RuntimeAuth | None:
    return _runtime_auth_var.get()


def set_runtime_auth(auth: RuntimeAuth) -> Token[RuntimeAuth | None]:
    return _runtime_auth_var.set(auth)


def reset_runtime_auth(token: Token[RuntimeAuth | None]) -> None:
    _runtime_auth_var.reset(token)


@contextmanager
def runtime_auth_scope(auth: RuntimeAuth):
    token = set_runtime_auth(auth)
    try:
        yield auth
    finally:
        reset_runtime_auth(token)


def get_developer_unlock_password() -> str:
    password = (os.getenv(DEV_UNLOCK_PASSWORD_ENV) or "").strip()
    return password or DEFAULT_DEV_UNLOCK_PASSWORD


def _has_project_service_key() -> bool:
    return bool((os.getenv("BAILIAN_API_KEY") or "").strip() or (os.getenv("DASHSCOPE_API_KEY") or "").strip())


def resolve_runtime_auth(user_api_key: str | None = None, debug_password: str | None = None) -> RuntimeAuth:
    api_key = (user_api_key or "").strip()
    if api_key:
        return RuntimeAuth(source="user", user_api_key=api_key)

    password = (debug_password or "").strip()
    expected_password = get_developer_unlock_password()
    if password and hmac.compare_digest(password, expected_password):
        if not _has_project_service_key():
            raise HTTPException(status_code=503, detail="开发者模式不可用：服务端未配置项目 API Key")
        return RuntimeAuth(source="project")

    raise HTTPException(
        status_code=401,
        detail="未配置可用的 API Key；请填写你的 API Key，或开启开发者模式并输入正确密码",
    )


def require_runtime_auth(
    x_user_api_key: Annotated[str | None, Header(alias="X-User-Api-Key")] = None,
    x_debug_unlock_password: Annotated[str | None, Header(alias="X-Debug-Unlock-Password")] = None,
) -> RuntimeAuth:
    return resolve_runtime_auth(x_user_api_key, x_debug_unlock_password)
