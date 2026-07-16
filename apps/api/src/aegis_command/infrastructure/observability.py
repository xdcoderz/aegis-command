from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest

from aegis_command.domain.models import EnforcementResult, SessionAssessment


class OperationalMetrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry(auto_describe=True)
        self.http_requests = Counter(
            "aegis_command_http_requests_total",
            "HTTP requests handled by the API",
            ("method", "route", "status"),
            registry=self.registry,
        )
        self.http_duration = Histogram(
            "aegis_command_http_request_duration_seconds",
            "HTTP request duration",
            ("method", "route"),
            registry=self.registry,
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
        )
        self.assessments = Counter(
            "aegis_command_assessments_total",
            "Privileged-session assessments",
            ("decision", "idempotent"),
            registry=self.registry,
        )
        self.enforcement = Counter(
            "aegis_command_enforcement_total",
            "Enforcement adapter outcomes",
            ("adapter", "status"),
            registry=self.registry,
        )

    def record_http(self, method: str, route: str, status_code: int, duration: float) -> None:
        self.http_requests.labels(method=method, route=route, status=str(status_code)).inc()
        self.http_duration.labels(method=method, route=route).observe(duration)

    def record_assessment(self, assessment: SessionAssessment, *, idempotent: bool) -> None:
        self.assessments.labels(
            decision=assessment.decision.value, idempotent=str(idempotent).lower()
        ).inc()

    def record_enforcement(self, result: EnforcementResult, adapter: str) -> None:
        self.enforcement.labels(adapter=adapter, status=result.status.value).inc()

    def render(self) -> bytes:
        return generate_latest(self.registry)
