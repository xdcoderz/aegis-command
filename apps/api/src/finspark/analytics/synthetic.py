from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from finspark.domain.models import SessionEvent

ROLE_PROFILES = {
    "database-admin": {
        "resources": ["customer-db", "reporting-db", "replica-db"],
        "commands": ["select health", "show replication", "backup verify", "explain query"],
        "sensitivity": 0.75,
    },
    "platform-admin": {
        "resources": ["payments-api", "kubernetes-prod", "observability"],
        "commands": ["kubectl get pods", "view logs", "check deployment", "restart canary"],
        "sensitivity": 0.8,
    },
    "security-admin": {
        "resources": ["identity-service", "siem", "certificate-service"],
        "commands": ["review policy", "query alerts", "rotate test key", "list sessions"],
        "sensitivity": 0.85,
    },
}


class SyntheticSessionGenerator:
    def __init__(self, seed: int) -> None:
        self._random = random.Random(seed)
        self._base = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)

    def normal(self, index: int) -> SessionEvent:
        roles = tuple(ROLE_PROFILES)
        role = roles[index % len(roles)]
        user_number = index % 12
        profile = ROLE_PROFILES[role]
        hour = int(min(max(self._random.gauss(11, 2), 7), 18))
        duration = max(self._random.gauss(32, 9), 5)
        command_count = self._random.randint(2, 5)
        commands = [self._random.choice(profile["commands"]) for _ in range(command_count)]
        return SessionEvent(
            session_id=f"baseline-{index:05d}",
            user_id=f"admin-{user_number:02d}",
            role=role,
            occurred_at=self._base + timedelta(days=index // 12, hours=hour),
            source_ip=f"10.20.{user_number}.15",
            device_id=f"managed-{user_number:02d}",
            resource=self._random.choice(profile["resources"]),
            resource_sensitivity=float(profile["sensitivity"]),
            commands=commands,
            session_duration_minutes=duration,
            privilege_level=3,
            bytes_transferred=self._random.randint(1_000, 150_000),
            approved_for_baseline=True,
        )

    def training_set(self, count: int = 480) -> list[SessionEvent]:
        return [self.normal(index) for index in range(count)]

