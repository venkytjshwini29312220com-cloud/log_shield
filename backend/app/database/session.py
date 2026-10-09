"""SQLite engine and sessions. Paths are resolved against the backend directory."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import BACKEND_DIR, get_settings
from app.database.base import Base

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def resolve_database_url(url: str, base_dir: Path = BACKEND_DIR) -> str:
    if not url.startswith("sqlite:///"):
        return url
    raw_path = url.removeprefix("sqlite:///")
    if raw_path.startswith("/") and not (len(raw_path) > 1 and raw_path[1] == ":"):
        path = Path(raw_path)
    else:
        path = Path(raw_path)
        if not path.is_absolute():
            path = (base_dir / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path.as_posix()}"


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        url = resolve_database_url(settings.database_url)
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            future=True,
        )

        @event.listens_for(_engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def init_db() -> None:
    from app.database import seed
    from app.models import orm as _orm  # noqa: F401 — register tables on Base.metadata

    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    session = get_session_factory()()
    try:
        seed.seed_defaults(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
