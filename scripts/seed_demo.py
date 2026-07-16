#!/usr/bin/env python3
"""Reset and seed the Aegis Command reference scenario dataset.

The reset path is deliberately fixed to apps/api/aegis-command.db. This utility will
not delete data from a configured PostgreSQL instance or from an arbitrary file.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from uuid import UUID, uuid5


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEMO_DB = (PROJECT_ROOT / "apps" / "api" / "aegis-command.db").resolve()
DEFAULT_API_BASE = "http://127.0.0.1:8000/api/v1/"
EVENT_NAMESPACE = UUID("d71437eb-ed67-552b-a518-55b7238327be")
RESET_TABLES = (
    "assessment_reviews",
    "session_actions",
    "assessments",
    "security_policy",
)
EXPECTED_COUNTS = {"ALLOW": 4, "STEP_UP_AUTH": 2, "BLOCK": 3}


class SeedError(RuntimeError):
    """A safe, user-facing seed failure."""


@dataclass(frozen=True, slots=True)
class DemoScenario:
    label: str
    expected_decision: str
    payload: dict[str, object]


def _most_recent_utc(now: datetime, hour: int, minute: int) -> datetime:
    candidate = now.astimezone(UTC).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    if candidate > now:
        candidate -= timedelta(days=1)
    return candidate


def _event_id(session_id: str) -> str:
    return str(uuid5(EVENT_NAMESPACE, session_id))


def _scenario(
    *,
    label: str,
    expected_decision: str,
    now: datetime,
    hour: int,
    minute: int,
    session_id: str,
    user_id: str,
    role: str,
    source_ip: str,
    device_id: str,
    resource: str,
    resource_sensitivity: float,
    commands: list[str],
    duration: float,
    privilege_level: int,
    privilege_escalated: bool = False,
    failed_auth_attempts: int = 0,
    bytes_transferred: int = 0,
) -> DemoScenario:
    occurred_at = _most_recent_utc(now, hour, minute)
    return DemoScenario(
        label=label,
        expected_decision=expected_decision,
        payload={
            "event_id": _event_id(session_id),
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "occurred_at": occurred_at.isoformat().replace("+00:00", "Z"),
            "source_ip": source_ip,
            "device_id": device_id,
            "resource": resource,
            "resource_sensitivity": resource_sensitivity,
            "commands": commands,
            "session_duration_minutes": duration,
            "privilege_level": privilege_level,
            "privilege_escalated": privilege_escalated,
            "failed_auth_attempts": failed_auth_attempts,
            "bytes_transferred": bytes_transferred,
            "approved_for_baseline": False,
        },
    )


def build_scenarios(now: datetime | None = None) -> tuple[DemoScenario, ...]:
    """Return the nine curated, repeatable privileged-session scenarios."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    return (
        _scenario(
            label="Daily ledger reconciliation",
            expected_decision="ALLOW",
            now=now,
            hour=10,
            minute=15,
            session_id="bnk-db-recon-0726",
            user_id="admin-00",
            role="database-admin",
            source_ip="10.20.0.15",
            device_id="managed-00",
            resource="reporting-db",
            resource_sensitivity=0.55,
            commands=["show replication", "select health", "backup verify"],
            duration=31,
            privilege_level=3,
            bytes_transferred=84_000,
        ),
        _scenario(
            label="Payments canary check",
            expected_decision="ALLOW",
            now=now,
            hour=11,
            minute=5,
            session_id="bnk-payments-canary-0726",
            user_id="admin-01",
            role="platform-admin",
            source_ip="10.20.1.15",
            device_id="managed-01",
            resource="payments-api",
            resource_sensitivity=0.80,
            commands=["view logs", "check deployment", "restart canary"],
            duration=27,
            privilege_level=3,
            bytes_transferred=128_000,
        ),
        _scenario(
            label="Morning SIEM review",
            expected_decision="ALLOW",
            now=now,
            hour=12,
            minute=20,
            session_id="bnk-siem-review-0726",
            user_id="admin-02",
            role="security-admin",
            source_ip="10.20.2.15",
            device_id="managed-02",
            resource="siem",
            resource_sensitivity=0.72,
            commands=["query alerts", "list sessions", "review policy"],
            duration=34,
            privilege_level=3,
            bytes_transferred=61_000,
        ),
        _scenario(
            label="Scheduled IAM key rotation",
            expected_decision="ALLOW",
            now=now,
            hour=13,
            minute=10,
            session_id="bnk-iam-key-rotation-0726",
            user_id="admin-05",
            role="security-admin",
            source_ip="10.20.5.15",
            device_id="managed-05",
            resource="identity-service",
            resource_sensitivity=0.85,
            commands=["rotate test key", "review policy", "list sessions"],
            duration=29,
            privilege_level=3,
            bytes_transferred=44_000,
        ),
        _scenario(
            label="Payments maintenance from recovery console",
            expected_decision="STEP_UP_AUTH",
            now=now,
            hour=13,
            minute=40,
            session_id="bnk-payments-recovery-0726",
            user_id="admin-07",
            role="platform-admin",
            source_ip="10.20.7.15",
            device_id="managed-07",
            resource="payments-api",
            resource_sensitivity=0.86,
            commands=["view logs", "check deployment", "restart canary"],
            duration=16,
            privilege_level=4,
            failed_auth_attempts=1,
            bytes_transferred=780_000,
        ),
        _scenario(
            label="IAM policy change after failed sign-in",
            expected_decision="STEP_UP_AUTH",
            now=now,
            hour=13,
            minute=25,
            session_id="bnk-iam-policy-review-0726",
            user_id="admin-08",
            role="security-admin",
            source_ip="10.20.8.15",
            device_id="managed-08",
            resource="identity-service",
            resource_sensitivity=0.90,
            commands=["review policy", "list sessions", "query alerts"],
            duration=16,
            privilege_level=4,
            failed_auth_attempts=1,
            bytes_transferred=240_000,
        ),
        _scenario(
            label="Core banking ledger export from an unmanaged host",
            expected_decision="BLOCK",
            now=now,
            hour=2,
            minute=12,
            session_id="bnk-core-ledger-exfil-0726",
            user_id="admin-03",
            role="database-admin",
            source_ip="198.51.100.77",
            device_id="unmanaged-win-77",
            resource="core-banking-ledger",
            resource_sensitivity=1.0,
            commands=["mimikatz credential dump", "disable audit", "export customer ledger"],
            duration=4,
            privilege_level=5,
            privilege_escalated=True,
            failed_auth_attempts=5,
            bytes_transferred=68_000_000,
        ),
        _scenario(
            label="SWIFT gateway credential staging",
            expected_decision="BLOCK",
            now=now,
            hour=1,
            minute=38,
            session_id="bnk-swift-credential-stage-0726",
            user_id="admin-04",
            role="platform-admin",
            source_ip="203.0.113.54",
            device_id="unregistered-linux-54",
            resource="swift-payment-gateway",
            resource_sensitivity=1.0,
            commands=["curl credential bundle", "scp swift-config backup-host", "disable audit"],
            duration=6,
            privilege_level=5,
            privilege_escalated=True,
            failed_auth_attempts=4,
            bytes_transferred=42_000_000,
        ),
        _scenario(
            label="Break-glass IAM account tampering",
            expected_decision="BLOCK",
            now=now,
            hour=3,
            minute=5,
            session_id="bnk-iam-breakglass-0726",
            user_id="admin-11",
            role="security-admin",
            source_ip="192.0.2.91",
            device_id="unknown-vdi-91",
            resource="identity-service",
            resource_sensitivity=0.98,
            commands=["net user /add emergency-admin", "clear-eventlog security", "disable audit"],
            duration=5,
            privilege_level=5,
            privilege_escalated=True,
            failed_auth_attempts=6,
            bytes_transferred=5_400_000,
        ),
    )


def validate_api_base(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SeedError("The seed utility only accepts an HTTP loopback API address.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise SeedError("The local API address cannot contain credentials, a query, or a fragment.")
    path = parsed.path.rstrip("/")
    if path != "/api/v1":
        raise SeedError("The local API address must end with /api/v1.")
    return value.rstrip("/") + "/"


def validate_local_database(path: Path = LOCAL_DEMO_DB) -> Path:
    resolved = path.resolve()
    if resolved != LOCAL_DEMO_DB:
        raise SeedError(f"Refusing to reset an unexpected database: {resolved}")
    if not resolved.is_file():
        raise SeedError(f"Local demo database does not exist: {resolved}")
    with resolved.open("rb") as database_file:
        if database_file.read(16) != b"SQLite format 3\x00":
            raise SeedError(f"Expected a SQLite database at: {resolved}")
    with sqlite3.connect(resolved) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    missing = set(RESET_TABLES) - tables
    if missing:
        raise SeedError(f"Database schema is incomplete; missing: {', '.join(sorted(missing))}")
    return resolved


def reset_local_database(path: Path = LOCAL_DEMO_DB) -> dict[str, int]:
    resolved = validate_local_database(path)
    deleted: dict[str, int] = {}
    with sqlite3.connect(resolved, timeout=10) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        try:
            for table in RESET_TABLES:
                before = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                connection.execute(f"DELETE FROM {table}")
                deleted[table] = int(before)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return deleted


class LocalApiClient:
    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        self.base_url = validate_api_base(base_url)
        self.api_key = api_key

    def request(
        self, method: str, path: str, payload: dict[str, object] | None = None
    ) -> tuple[int, Any, dict[str, str]]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {
            "Accept": "application/json",
            "X-Demo-Actor": "reference-scenario-seed",
        }
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        request = Request(
            urljoin(self.base_url, path.lstrip("/")),
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=10) as response:  # noqa: S310 - loopback is validated
                response_body = response.read().decode("utf-8")
                decoded = json.loads(response_body) if response_body else None
                return response.status, decoded, dict(response.headers.items())
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise SeedError(f"API {method} {path} returned {exc.code}: {detail}") from exc
        except URLError as exc:
            raise SeedError(f"Cannot reach the Aegis Command API at {self.base_url}: {exc.reason}") from exc


def _print_scenarios(scenarios: tuple[DemoScenario, ...], *, verbose: bool = False) -> None:
    print("Aegis Command reference scenarios")
    print("---------------------------------")
    for scenario in scenarios:
        payload = scenario.payload
        print(
            f"{scenario.expected_decision:12}  {payload['session_id']:<34} "
            f"{payload['user_id']:<9} {payload['resource']}"
        )
        if verbose:
            print(f"  {scenario.label}")
            print(f"  event {payload['event_id']} at {payload['occurred_at']}")


def seed(client: LocalApiClient, scenarios: tuple[DemoScenario, ...]) -> dict[str, int]:
    status, ready, _ = client.request("GET", "health/ready")
    if status != 200 or not isinstance(ready, dict) or ready.get("status") != "ready":
        raise SeedError(f"Local API is not ready: {ready}")

    _, current_policy, _ = client.request("GET", "policies")
    desired_policy = {"step_up_threshold": 40, "block_threshold": 70}
    if not isinstance(current_policy, dict) or any(
        float(current_policy.get(key, -1)) != value
        for key, value in desired_policy.items()
    ):
        client.request("PUT", "policies", desired_policy)

    observed = {key: 0 for key in EXPECTED_COUNTS}
    mismatches: list[str] = []
    for scenario in scenarios:
        status, assessment, headers = client.request("POST", "assessments", scenario.payload)
        if status not in {200, 201} or not isinstance(assessment, dict):
            raise SeedError(f"Unexpected assessment response for {scenario.label}: {assessment}")
        decision = str(assessment.get("decision"))
        if decision in observed:
            observed[decision] += 1
        replayed = headers.get("x-idempotent-replay", "false").lower() == "true"
        marker = "replayed" if replayed else "created"
        score = float(assessment.get("risk_score", 0))
        print(
            f"{marker:8} {scenario.payload['session_id']:<34} "
            f"{decision:<12} {score:5.1f}/100"
        )
        if decision != scenario.expected_decision:
            mismatches.append(
                f"{scenario.payload['session_id']}: expected {scenario.expected_decision}, got {decision}"
            )

    if mismatches:
        raise SeedError("Seed decision check failed:\n  " + "\n  ".join(mismatches))
    if observed != EXPECTED_COUNTS:
        raise SeedError(f"Expected decision mix {EXPECTED_COUNTS}, observed {observed}")
    return observed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed deterministic reference scenarios through the Aegis Command API."
    )
    parser.add_argument(
        "--api-base",
        default=DEFAULT_API_BASE,
        help="Loopback API base ending in /api/v1 (default: %(default)s)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("AEGIS_DEMO_API_KEY"),
        help="Admin API key when local authentication is enabled.",
    )
    parser.add_argument(
        "--reset-local-db",
        action="store_true",
        help="Delete existing demo records from apps/api/aegis-command.db before seeding.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and show the plan without touching the database or API.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List the curated scenarios and exit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        api_base = validate_api_base(args.api_base)
        scenarios = build_scenarios()
        if args.list:
            _print_scenarios(scenarios, verbose=True)
            return 0
        if args.dry_run:
            print(f"API:      {api_base}")
            print(f"Database: {LOCAL_DEMO_DB}")
            print(f"Reset:    {'yes' if args.reset_local_db else 'no'}")
            _print_scenarios(scenarios, verbose=True)
            print("\nDry run complete; no database or API changes were made.")
            return 0

        client = LocalApiClient(api_base, args.api_key)
        status, ready, _ = client.request("GET", "health/ready")
        if status != 200 or not isinstance(ready, dict) or ready.get("status") != "ready":
            raise SeedError(f"Local API is not ready: {ready}")

        if args.reset_local_db:
            deleted = reset_local_database()
            print(f"Reset verified local database: {LOCAL_DEMO_DB}")
            for table in RESET_TABLES:
                print(f"  cleared {table:<20} {deleted[table]:>3} row(s)")
            _, remaining, _ = client.request("GET", "assessments?limit=1")
            if remaining != []:
                raise SeedError(
                    "The running API is not reading the verified local SQLite database. "
                    "No seed records were posted."
                )

        print("\nSeeding sessions")
        observed = seed(client, scenarios)
        print(
            "\nReference dataset ready: "
            f"{observed['ALLOW']} allow, "
            f"{observed['STEP_UP_AUTH']} step-up, "
            f"{observed['BLOCK']} block."
        )
        return 0
    except (SeedError, OSError, sqlite3.Error, ValueError) as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
