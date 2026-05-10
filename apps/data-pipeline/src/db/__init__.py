from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Lock
from typing import Iterator

from sqlalchemy import Connection, Engine, create_engine

from src.config.settings import settings

_engine: Engine | None = None
_engine_lock = Lock()


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                _engine = create_engine(settings.database_url, future=True)
    return _engine


@contextmanager
def get_connection() -> Iterator[Connection]:
    engine = get_engine()
    with engine.begin() as connection:
        yield connection


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


__all__ = ["get_connection", "get_engine", "utcnow"]
