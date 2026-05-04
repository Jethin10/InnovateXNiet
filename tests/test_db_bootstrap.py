from sqlalchemy import create_engine, inspect, text

from app.db.base import Base
from app.db.management import initialize_database
from app.db.models import (
    AssessmentSessionRecord,
    ResumeArtifact,
    RoadmapSnapshot,
    StudentProfile,
    TrustScoreRecord,
    TrustStampProfileRecord,
    User,
)


def test_database_metadata_bootstraps_expected_tables(tmp_path):
    database_path = tmp_path / "backend.db"
    engine = create_engine(f"sqlite:///{database_path}")

    Base.metadata.create_all(engine)
    table_names = set(inspect(engine).get_table_names())

    assert User.__tablename__ in table_names
    assert StudentProfile.__tablename__ in table_names
    assert ResumeArtifact.__tablename__ in table_names
    assert AssessmentSessionRecord.__tablename__ in table_names
    assert TrustScoreRecord.__tablename__ in table_names
    assert RoadmapSnapshot.__tablename__ in table_names
    assert TrustStampProfileRecord.__tablename__ in table_names


def test_initialize_database_adds_new_columns_to_existing_sqlite_database(tmp_path):
    database_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE users ("
                "id INTEGER PRIMARY KEY, "
                "email VARCHAR(255), "
                "full_name VARCHAR(255) NOT NULL, "
                "role VARCHAR(64) NOT NULL, "
                "created_at DATETIME, "
                "updated_at DATETIME)"
            )
        )
        connection.execute(
            text(
                "CREATE TABLE resume_artifacts ("
                "id INTEGER PRIMARY KEY, "
                "student_profile_id INTEGER NOT NULL, "
                "filename VARCHAR(255), "
                "raw_text TEXT NOT NULL, "
                "parse_status VARCHAR(64) NOT NULL, "
                "extracted_claims_json TEXT NOT NULL, "
                "created_at DATETIME, "
                "updated_at DATETIME)"
            )
        )

    initialize_database(engine)
    columns_by_table = {
        table_name: {column["name"] for column in inspect(engine).get_columns(table_name)}
        for table_name in ("users", "resume_artifacts")
    }

    assert "password_hash" in columns_by_table["users"]
    assert "analysis_json" in columns_by_table["resume_artifacts"]
