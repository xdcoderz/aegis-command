from datetime import UTC, datetime

from finspark.analytics.risk import RiskPolicy
from finspark.analytics.runtime import DetectionRuntime
from finspark.analytics.synthetic import SyntheticSessionGenerator
from finspark.domain.models import AccessDecision, SessionEvent


def test_malicious_session_scores_above_normal_session() -> None:
    runtime = DetectionRuntime.bootstrap(seed=2026, contamination=0.08)
    normal = SyntheticSessionGenerator(9001).normal(0)
    malicious = SessionEvent(
        session_id="attack-001",
        user_id="admin-00",
        role="database-admin",
        occurred_at=datetime(2026, 3, 1, 2, 15, tzinfo=UTC),
        source_ip="198.51.100.77",
        device_id="unmanaged-laptop",
        resource="core-banking-master",
        resource_sensitivity=1.0,
        commands=["mimikatz credential dump", "disable audit", "scp customer.dump remote"],
        session_duration_minutes=2,
        privilege_level=5,
        privilege_escalated=True,
        failed_auth_attempts=4,
        bytes_transferred=50_000_000,
    )

    _, normal_score, _ = runtime.assess_features(normal)
    malicious_features, malicious_score, scope = runtime.assess_features(malicious)

    assert malicious_score > normal_score
    assert malicious_features["resource_novelty"] == 1
    assert malicious_features["deterministic_rule"] == 1
    assert scope == "user:admin-00"


def test_high_risk_signals_are_blocked() -> None:
    features = {
        "asset_sensitivity": 1.0,
        "privilege_context": 1.0,
        "session_context": 1.0,
        "deterministic_rule": 1.0,
    }
    score, decision, factors = RiskPolicy().evaluate(1.0, features)

    assert score == 100
    assert decision is AccessDecision.BLOCK
    assert sum(factor.score for factor in factors) == 100


def test_runtime_policy_thresholds_change_future_decisions() -> None:
    features = {
        "asset_sensitivity": 0.0,
        "privilege_context": 0.0,
        "session_context": 0.0,
        "deterministic_rule": 0.0,
    }
    policy = RiskPolicy(step_up_threshold=20, block_threshold=40)

    score, initial, _ = policy.evaluate(0.5, features)
    policy.configure(step_up_threshold=10, block_threshold=25)
    _, updated, _ = policy.evaluate(0.5, features)

    assert score == 30
    assert initial is AccessDecision.STEP_UP_AUTH
    assert updated is AccessDecision.BLOCK
