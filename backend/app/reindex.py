from app.db import init_db, session_factory
from app.managers.ingest_manager import IngestManager
from app.settings.config import get_config


def main() -> None:
    config = get_config()
    init_db(config)
    db = session_factory()()
    try:
        IngestManager(session=db, config=config).refresh_embeddings()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
