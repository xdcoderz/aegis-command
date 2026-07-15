from __future__ import annotations

from typing import ClassVar

from finspark.domain.models import AccessDecision, RiskFactor


class RiskPolicy:
    weights: ClassVar[dict[str, float]] = {
        "behavior": 0.60,
        "asset": 0.15,
        "privilege": 0.10,
        "session": 0.10,
        "rule": 0.05,
    }

    def evaluate(
        self, anomaly_score: float, features: dict[str, float]
    ) -> tuple[float, AccessDecision, list[RiskFactor]]:
        values = {
            "behavior": anomaly_score,
            "asset": features["asset_sensitivity"],
            "privilege": features["privilege_context"],
            "session": features["session_context"],
            "rule": features["deterministic_rule"],
        }
        labels = {
            "behavior": "Behavioral anomaly",
            "asset": "Asset sensitivity",
            "privilege": "Privilege context",
            "session": "Session context",
            "rule": "Deterministic threat rule",
        }
        factors = [
            RiskFactor(
                key=key,
                label=labels[key],
                score=round(value * self.weights[key] * 100, 2),
                evidence=f"normalized signal={value:.2f}; policy weight={self.weights[key]:.2f}",
            )
            for key, value in values.items()
        ]
        score = round(sum(factor.score for factor in factors), 2)
        if score >= 70:
            decision = AccessDecision.BLOCK
        elif score >= 40:
            decision = AccessDecision.STEP_UP_AUTH
        else:
            decision = AccessDecision.ALLOW
        return score, decision, factors
