from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from statistics import fmean, pstdev

from finspark.domain.models import SessionEvent


def _safe_std(values: list[float]) -> float:
    return max(pstdev(values), 1.0) if len(values) > 1 else 1.0


@dataclass(frozen=True, slots=True)
class BaselineProfile:
    scope: str
    hour_sin: float
    hour_cos: float
    duration_mean: float
    duration_std: float
    action_rate_mean: float
    action_rate_std: float
    resources: frozenset[str]
    commands: frozenset[str]
    source_ips: frozenset[str]
    device_ids: frozenset[str]

    @classmethod
    def from_events(cls, scope: str, events: list[SessionEvent]) -> BaselineProfile:
        if not events:
            raise ValueError("A baseline requires at least one event")
        radians = [event.occurred_at.hour / 24 * 2 * math.pi for event in events]
        durations = [event.session_duration_minutes for event in events]
        action_rates = [len(event.commands) / event.session_duration_minutes for event in events]
        command_counts = Counter(command.lower() for event in events for command in event.commands)
        return cls(
            scope=scope,
            hour_sin=fmean(math.sin(value) for value in radians),
            hour_cos=fmean(math.cos(value) for value in radians),
            duration_mean=fmean(durations),
            duration_std=_safe_std(durations),
            action_rate_mean=fmean(action_rates),
            action_rate_std=_safe_std(action_rates),
            resources=frozenset(event.resource for event in events),
            commands=frozenset(command for command, count in command_counts.items() if count >= 2),
            source_ips=frozenset(event.source_ip for event in events),
            device_ids=frozenset(event.device_id for event in events),
        )


class BaselineCatalog:
    def __init__(self) -> None:
        self._user: dict[str, BaselineProfile] = {}
        self._role: dict[str, BaselineProfile] = {}
        self._global: BaselineProfile | None = None

    def fit(self, events: list[SessionEvent]) -> None:
        approved = [event for event in events if event.approved_for_baseline]
        if not approved:
            raise ValueError("No approved baseline events were supplied")
        by_user: defaultdict[str, list[SessionEvent]] = defaultdict(list)
        by_role: defaultdict[str, list[SessionEvent]] = defaultdict(list)
        for event in approved:
            by_user[event.user_id].append(event)
            by_role[event.role].append(event)
        self._user = {
            key: BaselineProfile.from_events(f"user:{key}", value)
            for key, value in by_user.items()
            if len(value) >= 8
        }
        self._role = {
            key: BaselineProfile.from_events(f"role:{key}", value)
            for key, value in by_role.items()
        }
        self._global = BaselineProfile.from_events("global", approved)

    def resolve(self, event: SessionEvent) -> BaselineProfile:
        if event.user_id in self._user:
            return self._user[event.user_id]
        if event.role in self._role:
            return self._role[event.role]
        if self._global is None:
            raise RuntimeError("Baseline catalog is not fitted")
        return self._global

