from app.db import init_db, session_factory
from app.ingest_runner import run_ingest_job
from app.settings.config import get_config


def main() -> None:
    config = get_config()
    init_db(config)
    session_factory()
    run_ingest_job()


if __name__ == "__main__":
    main()
