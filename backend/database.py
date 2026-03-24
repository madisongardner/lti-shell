import os

from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker

DEFAULT_SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'lti_shell.db')
DATABASE_URL = os.getenv('DATABASE_URL', f'sqlite:///{DEFAULT_SQLITE_PATH}')
ATTEMPT_INACTIVITY_MINUTES = int(os.getenv('LTI_SHELL_ATTEMPT_INACTIVITY_MINUTES', '15'))
ENGINE_KWARGS = {}
if DATABASE_URL.startswith('sqlite'):
    # Background cleanup runs in a separate thread; allow shared SQLite connections.
    ENGINE_KWARGS['connect_args'] = {'check_same_thread': False}

engine = create_engine(DATABASE_URL, **ENGINE_KWARGS)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # Import model modules so SQLAlchemy can register tables before create_all.
    import models.assignment  # noqa: F401
    import models.attempt  # noqa: F401
    import models.audit_log  # noqa: F401
    import models.submission  # noqa: F401
    import models.user  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_schema_columns()


def _ensure_schema_columns():
    # Lightweight migration for SQLite dev DBs to keep existing local data usable.
    if not str(engine.url).startswith('sqlite'):
        return

    with engine.begin() as conn:
        rows = conn.execute(text('PRAGMA table_info(assignments)')).fetchall()
        if rows:
            assignment_columns = {row[1] for row in rows}
            if 'grading_feature' not in assignment_columns:
                conn.execute(
                    text("ALTER TABLE assignments ADD COLUMN grading_feature VARCHAR(64) NOT NULL DEFAULT 'script_zip'")
                )
            if 'grading_config_json' not in assignment_columns:
                conn.execute(
                    text("ALTER TABLE assignments ADD COLUMN grading_config_json TEXT NOT NULL DEFAULT '{}'")
                )

        attempt_rows = conn.execute(text('PRAGMA table_info(attempts)')).fetchall()
        if not attempt_rows:
            return

        attempt_columns = {row[1] for row in attempt_rows}
        if 'last_activity_at' not in attempt_columns:
            conn.execute(
                text("ALTER TABLE attempts ADD COLUMN last_activity_at DATETIME")
            )
            conn.execute(
                text("UPDATE attempts SET last_activity_at = COALESCE(created_at, CURRENT_TIMESTAMP)")
            )

        # Normalize active attempts to inactivity-based expiration window.
        conn.execute(
            text(
                """
                UPDATE attempts
                SET expires_at = datetime(last_activity_at, :window_sql)
                WHERE status IN ('created', 'running')
                """
            ),
            {'window_sql': f'+{ATTEMPT_INACTIVITY_MINUTES} minutes'},
        )
