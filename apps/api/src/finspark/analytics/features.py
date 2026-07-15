from __future__ import annotations

import math

from finspark.analytics.baseline import BaselineProfile
from finspark.domain.models import SessionEvent

MODEL_FEATURES = (
    "hour_deviation",
    "duration_deviation",
    "action_rate_deviation",
    "resource_novelty",
    "command_novelty",
    "source_ip_novelty",
    "device_novelty",
    "transfer_intensity",
)

SUSPICIOUS_COMMAND_MARKERS = (
    "mimikatz",
    "credential dump",
    "shadow copy",
    "disable audit",
    "clear-eventlog",
    "net user /add",
    "chmod 777",
    "curl ",
    "scp ",
)


def _bounded_deviation(value: float, mean: float, std: float) -> float:
    return min(abs(value - mean) / max(std * 4, 1e-6), 1.0)


def extract_features(event: SessionEvent, baseline: BaselineProfile) -> dict[str, float]:
    radians = event.occurred_at.hour / 24 * 2 * math.pi
    circular_distance = math.sqrt(
        (math.sin(radians) - baseline.hour_sin) ** 2
        + (math.cos(radians) - baseline.hour_cos) ** 2
    ) / 2
    action_rate = len(event.commands) / event.session_duration_minutes
    normalized_commands = [command.lower() for command in event.commands]
    novel_command_count = sum(command not in baseline.commands for command in normalized_commands)
    command_novelty = novel_command_count / len(normalized_commands)
    suspicious = any(
        marker in command
        for marker in SUSPICIOUS_COMMAND_MARKERS
        for command in normalized_commands
    )
    return {
        "hour_deviation": min(circular_distance, 1.0),
        "duration_deviation": _bounded_deviation(
            event.session_duration_minutes, baseline.duration_mean, baseline.duration_std
        ),
        "action_rate_deviation": _bounded_deviation(
            action_rate, baseline.action_rate_mean, baseline.action_rate_std
        ),
        "resource_novelty": float(event.resource not in baseline.resources),
        "command_novelty": command_novelty,
        "source_ip_novelty": float(event.source_ip not in baseline.source_ips),
        "device_novelty": float(event.device_id not in baseline.device_ids),
        "transfer_intensity": min(event.bytes_transferred / 10_000_000, 1.0),
        "asset_sensitivity": event.resource_sensitivity,
        "privilege_context": max(float(event.privilege_escalated), (event.privilege_level - 1) / 4),
        "session_context": max(
            min(circular_distance, 1.0),
            float(event.source_ip not in baseline.source_ips),
            float(event.device_id not in baseline.device_ids),
            min(event.failed_auth_attempts / 5, 1.0),
        ),
        "deterministic_rule": float(suspicious),
    }


def model_vector(features: dict[str, float]) -> list[float]:
    return [features[name] for name in MODEL_FEATURES]
