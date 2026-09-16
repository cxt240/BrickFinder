from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.entities import Base
from app.settings.config import Config, get_config

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine(config: Config | None = None) -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        config = config or get_config()
        config.data_path.mkdir(parents=True, exist_ok=True)
        config.db_dir.mkdir(parents=True, exist_ok=True)
        config.media_path.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            config.sqlite_url,
            future=True,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(_engine, "connect")
        def _on_connect(dbapi_conn, _connection_record) -> None:  # type: ignore[no-untyped-def]
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


def init_db(config: Config | None = None) -> None:
    engine = get_engine(config)
    Base.metadata.create_all(engine)


def session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def relative_to_data(path: Path, data_path: Path) -> str:
    return path.resolve().relative_to(data_path.resolve()).as_posix()


def absolute_from_data(relpath: str, data_path: Path) -> Path:
    root = data_path.resolve()
    full = (root / relpath).resolve()
    if root not in full.parents and full != root:
        raise ValueError("path escapes data directory")
    return full
