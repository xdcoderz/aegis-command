from __future__ import annotations

import sqlite3
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.seed_demo import (
    LOCAL_DEMO_DB,
    RESET_TABLES,
    SeedError,
    build_scenarios,
    reset_local_database,
    validate_api_base,
    validate_local_database,
)


def _demo_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE assessments (id TEXT)")
        connection.execute("CREATE TABLE assessment_reviews (id TEXT)")
        connection.execute("CREATE TABLE session_actions (id TEXT)")
        connection.execute("CREATE TABLE security_policy (id TEXT)")
        for table in RESET_TABLES:
            connection.execute(f"INSERT INTO {table} VALUES ('record')")


def test_scenarios_have_deterministic_ids_and_expected_mix() -> None:
    now = datetime(2026, 7, 16, 18, 30, tzinfo=UTC)
    first = build_scenarios(now)
    second = build_scenarios(now + timedelta(minutes=10))

    assert len(first) == 9
    assert Counter(item.expected_decision for item in first) == {
        "ALLOW": 4,
        "STEP_UP_AUTH": 2,
        "BLOCK": 3,
    }
    assert [item.payload["event_id"] for item in first] == [
        item.payload["event_id"] for item in second
    ]
    assert len({item.payload["session_id"] for item in first}) == 9
    assert len({item.payload["user_id"] for item in first}) == 9
    assert all("not-captured" not in str(item.payload).lower() for item in first)
    for item in first:
        occurred = datetime.fromisoformat(str(item.payload["occurred_at"]).replace("Z", "+00:00"))
        assert timedelta(0) <= now - occurred < timedelta(hours=24)


def test_api_base_accepts_only_loopback_v1() -> None:
    assert validate_api_base("http://localhost:8000/api/v1") == (
        "http://localhost:8000/api/v1/"
    )
    with pytest.raises(SeedError):
        validate_api_base("https://demo.example.com/api/v1")
    with pytest.raises(SeedError):
        validate_api_base("http://127.0.0.1:8000/api/v2")


def test_database_guard_rejects_every_path_except_project_database(tmp_path: Path) -> None:
    other = tmp_path / "aegis-command.db"
    _demo_database(other)

    with pytest.raises(SeedError, match="unexpected database"):
        validate_local_database(other)
    with pytest.raises(SeedError, match="unexpected database"):
        reset_local_database(other)

    assert LOCAL_DEMO_DB.name == "aegis-command.db"
    assert LOCAL_DEMO_DB.parent.name == "api"
