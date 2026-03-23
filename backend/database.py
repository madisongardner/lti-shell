from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///lti_shell.db')
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
        if not rows:
            return

        existing = {row[1] for row in rows}
        if 'grading_feature' not in existing:
            conn.execute(
                text("ALTER TABLE assignments ADD COLUMN grading_feature VARCHAR(64) NOT NULL DEFAULT 'script_zip'")
            )
        if 'grading_config_json' not in existing:
            conn.execute(
                text("ALTER TABLE assignments ADD COLUMN grading_config_json TEXT NOT NULL DEFAULT '{}'")
            )
