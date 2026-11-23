"""Real Alembic upgrades preserve legacy profiles without assuming eligibility."""

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

from services.common.config import get_settings
from services.common.models import User


ROOT = Path(__file__).resolve().parents[2]
PREVIOUS = "20261030_0010"
CURRENT = "20261121_0011"


@pytest.fixture()
def migration_database(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migration.db'}"
    monkeypatch.setattr(get_settings(), "database_url", url)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    engine = sa.create_engine(url)
    try:
        # Early migrations require PostgreSQL ALTER COLUMN support. Initialize
        # the actual legacy profile schema, then exercise this upgrade on SQLite.
        legacy_profile = ScriptDirectory.from_config(config).get_revision("20261027_0007")
        with engine.begin() as connection:
            User.__table__.create(connection)
            with Operations.context(MigrationContext.configure(connection)):
                legacy_profile.module.upgrade()
        command.stamp(config, PREVIOUS)
        yield config, engine
    finally:
        engine.dispose()


def test_legacy_profile_upgrade_keeps_inputs_and_null_confirmations(migration_database):
    config, engine = migration_database
    legacy = {
        "user_id": "legacy-profile-user", "age_years": 30, "height_cm": 175.0,
        "weight_kg": 70.0, "sex": "male", "goal": "gain_muscle",
        "activity_level": "moderate", "revision": 7,
        "created_at": "2026-10-01 00:00:00", "updated_at": "2026-10-30 00:00:00",
    }
    with engine.begin() as connection:
        connection.execute(sa.text(
            "INSERT INTO users (id, username, password_hash, created_at) "
            "VALUES (:id, :username, :password_hash, :created_at)"
        ), {
            "id": legacy["user_id"], "username": "legacy_profile_user",
            "password_hash": "synthetic-unused-hash", "created_at": legacy["created_at"],
        })
        connection.execute(sa.text(
            "INSERT INTO user_profiles (user_id, age_years, height_cm, weight_kg, "
            "sex, goal, activity_level, revision, created_at, updated_at) "
            "VALUES (:user_id, :age_years, :height_cm, :weight_kg, :sex, :goal, "
            ":activity_level, :revision, :created_at, :updated_at)"
        ), legacy)
    command.upgrade(config, "head")
    with engine.connect() as connection:
        row = dict(connection.execute(sa.text("SELECT * FROM user_profiles")).mappings().one())
        assert {field: row[field] for field in legacy} == legacy
        assert row["strength_training"] is None
        assert row["reference_scope"] is None
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == CURRENT
    with engine.begin() as connection:
        with pytest.raises(sa.exc.IntegrityError):
            connection.execute(sa.text(
                "UPDATE user_profiles SET reference_scope = 'inferred_eligible'"
            ))
    command.downgrade(config, PREVIOUS)
    with engine.connect() as connection:
        restored = dict(connection.execute(
            sa.text("SELECT * FROM user_profiles")
        ).mappings().one())
        assert restored == legacy
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM users")) == 1
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == PREVIOUS


def test_empty_legacy_profile_schema_reaches_head_with_nullable_confirmations(migration_database):
    config, engine = migration_database
    command.upgrade(config, "head")
    columns = {column["name"]: column for column in sa.inspect(engine).get_columns("user_profiles")}
    for field in ("strength_training", "reference_scope"):
        assert columns[field]["nullable"] is True
        assert columns[field]["default"] is None
    constraints = sa.inspect(engine).get_check_constraints("user_profiles")
    assert any(check["name"] == "ck_user_profiles_reference_scope" for check in constraints)
    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT version_num FROM alembic_version")) == CURRENT
        assert connection.scalar(sa.text("SELECT COUNT(*) FROM user_profiles")) == 0
