from __future__ import annotations

from finspark.analytics.baseline import BaselineCatalog
from finspark.analytics.features import extract_features, model_vector
from finspark.analytics.model import IsolationForestDetector
from finspark.analytics.synthetic import SyntheticSessionGenerator
from finspark.domain.models import SessionEvent


class DetectionRuntime:
    def __init__(self, baseline: BaselineCatalog, detector: IsolationForestDetector) -> None:
        self.baseline = baseline
        self.detector = detector

    @classmethod
    def bootstrap(cls, *, seed: int, contamination: float) -> DetectionRuntime:
        sessions = SyntheticSessionGenerator(seed).training_set()
        baseline = BaselineCatalog()
        baseline.fit(sessions)
        vectors = []
        for session in sessions:
            profile = baseline.resolve(session)
            vectors.append(model_vector(extract_features(session, profile)))
        detector = IsolationForestDetector(seed=seed, contamination=contamination)
        detector.fit(vectors)
        return cls(baseline, detector)

    def assess_features(self, event: SessionEvent) -> tuple[dict[str, float], float, str]:
        profile = self.baseline.resolve(event)
        features = extract_features(event, profile)
        anomaly = self.detector.score(model_vector(features))
        return features, anomaly, profile.scope

