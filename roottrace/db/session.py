from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from roottrace.config import Settings, settings

_ENGINE_CACHE: dict[str, sessionmaker[Session]] = {}


def get_sessionmaker(config: Settings = settings) -> sessionmaker[Session]:
    """Return a sessionmaker bound to the configured SQLite database."""

    key = str(config.db_path.resolve())
    if key not in _ENGINE_CACHE:
        config.db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            f"sqlite:///{config.db_path}",
            future=True,
            connect_args={"check_same_thread": False},
        )
        _ENGINE_CACHE[key] = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )
    return _ENGINE_CACHE[key]


@contextmanager
def session_scope(config: Settings = settings) -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""

    session_factory = get_sessionmaker(config)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


__all__ = ["session_scope", "get_sessionmaker"]
