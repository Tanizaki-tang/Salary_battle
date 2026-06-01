from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DEFAULT_SQLITE_PATH = Path(__file__).resolve().parents[1] / "app.db"

_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker[Session] | None = None
_ENGINE_URL: str | None = None


class Base(DeclarativeBase):
    pass


def _normalize_database_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://") and "+psycopg" not in url:
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def get_database_url() -> str:
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if raw_url:
        return _normalize_database_url(raw_url)
    return f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


def get_engine() -> Engine:
    global _ENGINE, _SESSION_FACTORY, _ENGINE_URL

    url = get_database_url()
    if _ENGINE is not None and _SESSION_FACTORY is not None and _ENGINE_URL == url:
        return _ENGINE

    connect_args: dict[str, object] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    _ENGINE = create_engine(
        url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    _SESSION_FACTORY = sessionmaker(bind=_ENGINE, autoflush=False, autocommit=False, future=True)
    _ENGINE_URL = url
    return _ENGINE


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SESSION_FACTORY is not None
    return _SESSION_FACTORY


def init_db() -> None:
    from app.repositories.db_models import CardGameSessionRecord, TextSessionRecord, TextSessionResultRecord

    del CardGameSessionRecord, TextSessionRecord, TextSessionResultRecord
    Base.metadata.create_all(bind=get_engine())


def reset_db_engine() -> None:
    global _ENGINE, _SESSION_FACTORY, _ENGINE_URL

    if _ENGINE is not None:
        _ENGINE.dispose()
    _ENGINE = None
    _SESSION_FACTORY = None
    _ENGINE_URL = None


@contextmanager
def db_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
