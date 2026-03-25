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
            if 'lineitem_url' not in assignment_columns:
                conn.execute(
                    text("ALTER TABLE assignments ADD COLUMN lineitem_url TEXT NOT NULL DEFAULT ''")
                )
            if 'grading_feature' not in assignment_columns:
                conn.execute(
                    text("ALTER TABLE assignments ADD COLUMN grading_feature VARCHAR(64) NOT NULL DEFAULT 'script_zip'")
                )
            if 'grading_config_json' not in assignment_columns:
                conn.execute(
                    text("ALTER TABLE assignments ADD COLUMN grading_config_json TEXT NOT NULL DEFAULT '{}'")
                )
            if 'starter_zip_path' not in assignment_columns:
                conn.execute(text("ALTER TABLE assignments ADD COLUMN starter_zip_path TEXT"))
            if 'tests_zip_path' not in assignment_columns:
                conn.execute(text("ALTER TABLE assignments ADD COLUMN tests_zip_path TEXT"))
            if 'starter_extracted_path' not in assignment_columns:
                conn.execute(text("ALTER TABLE assignments ADD COLUMN starter_extracted_path TEXT"))
            if 'tests_extracted_path' not in assignment_columns:
                conn.execute(text("ALTER TABLE assignments ADD COLUMN tests_extracted_path TEXT"))
            if 'has_required_test_runner' not in assignment_columns:
                conn.execute(
                    text("ALTER TABLE assignments ADD COLUMN has_required_test_runner BOOLEAN NOT NULL DEFAULT 0")
                )
            if 'artifacts_validated' not in assignment_columns:
                conn.execute(
                    text("ALTER TABLE assignments ADD COLUMN artifacts_validated BOOLEAN NOT NULL DEFAULT 0")
                )
            if 'artifact_validation_error' not in assignment_columns:
                conn.execute(
                    text("ALTER TABLE assignments ADD COLUMN artifact_validation_error TEXT NOT NULL DEFAULT ''")
                )

        submission_rows = conn.execute(text('PRAGMA table_info(submissions)')).fetchall()
        if submission_rows:
            submission_columns = {row[1] for row in submission_rows}
            if 'passback_status' not in submission_columns:
                conn.execute(
                    text("ALTER TABLE submissions ADD COLUMN passback_status VARCHAR(32) NOT NULL DEFAULT 'not_attempted'")
                )
            if 'passback_attempts' not in submission_columns:
                conn.execute(
                    text("ALTER TABLE submissions ADD COLUMN passback_attempts INTEGER NOT NULL DEFAULT 0")
                )
            if 'passback_last_error' not in submission_columns:
                conn.execute(
                    text("ALTER TABLE submissions ADD COLUMN passback_last_error TEXT NOT NULL DEFAULT ''")
                )
            if 'passback_completed_at' not in submission_columns:
                conn.execute(
                    text("ALTER TABLE submissions ADD COLUMN passback_completed_at DATETIME")
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
