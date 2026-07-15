from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest


class IsolationForestDetector:
    version = "isolation-forest-v1"

    def __init__(self, *, seed: int, contamination: float) -> None:
        self._model = IsolationForest(
            n_estimators=240,
            max_samples="auto",
            contamination=contamination,
            random_state=seed,
            n_jobs=-1,
        )
        self._low = 0.0
        self._high = 1.0
        self._fitted = False

    @property
    def fitted(self) -> bool:
        return self._fitted

    def fit(self, vectors: list[list[float]]) -> None:
        if len(vectors) < 50:
            raise ValueError("At least 50 baseline vectors are required")
        matrix = np.asarray(vectors, dtype=float)
        self._model.fit(matrix)
        raw = self._model.score_samples(matrix)
        self._low = float(np.quantile(raw, 0.01))
        self._high = float(np.quantile(raw, 0.95))
        if self._high <= self._low:
            self._high = self._low + 1e-6
        self._fitted = True

    def score(self, vector: list[float]) -> float:
        if not self._fitted:
            raise RuntimeError("Isolation Forest is not fitted")
        raw = float(self._model.score_samples(np.asarray([vector], dtype=float))[0])
        return min(max((self._high - raw) / (self._high - self._low), 0.0), 1.0)

