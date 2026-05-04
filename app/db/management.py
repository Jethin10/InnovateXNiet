from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from app.db.base import Base


def initialize_database(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    _apply_sqlite_compatibility_migrations(engine)


def _apply_sqlite_compatibility_migrations(engine: Engine) -> None:
    if engine.dialect.name != "sqlite":
        return

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    migrations = {
        "users": {
            "password_hash": "ALTER TABLE users ADD COLUMN password_hash TEXT",
        },
        "resume_artifacts": {
            "analysis_json": "ALTER TABLE resume_artifacts ADD COLUMN analysis_json TEXT DEFAULT '{}'",
        },
        "assessment_sessions": {
            "attempt_id": "ALTER TABLE assessment_sessions ADD COLUMN attempt_id INTEGER",
        },
    }

    with engine.begin() as connection:
        for table_name, column_migrations in migrations.items():
            if table_name not in table_names:
                continue
            columns = {
                row[1]
                for row in connection.execute(text(f"PRAGMA table_info({table_name})")).all()
            }
            for column_name, statement in column_migrations.items():
                if column_name not in columns:
                    connection.execute(text(statement))
