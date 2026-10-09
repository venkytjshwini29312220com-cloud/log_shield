"""Lightweight Isolation Forest anomaly detection engine for LogShield (Phase 6).

Unsupervised anomaly detector trained on synthetic baseline lab traffic.
Outputs risk scores in 0-100 (never attack probabilities). Emits alerts when risk exceeds threshold.
Pure-Python implementation to guarantee compatibility with all host environments.
"""

from datetime import datetime, timezone
import math
import random
from typing import Any

from sqlalchemy.orm import Session

from app.detection.engine import generate_next_alert_ids
from app.detection.features import FEATURE_NAMES, extract_features_from_db, vector_from_dict
from app.models.orm import Alert, Event


def _c_factor(n: int) -> float:
    """Average path length of unsuccessful search in Binary Search Tree."""
    if n <= 1:
        return 0.0
    if n == 2:
        return 1.0
    # Euler-Mascheroni constant ≈ 0.5772156649
    return 2.0 * (math.log(n - 1) + 0.5772156649) - (2.0 * (n - 1) / n)


class _IsolationTreeNode:
    def __init__(
        self,
        left: "_IsolationTreeNode | None" = None,
        right: "_IsolationTreeNode | None" = None,
        split_feature: int | None = None,
        split_value: float | None = None,
        size: int = 1,
    ) -> None:
        self.left = left
        self.right = right
        self.split_feature = split_feature
        self.split_value = split_value
        self.size = size
        self.is_leaf = left is None and right is None


def _build_itree(
    X: list[list[float]],
    current_height: int,
    height_limit: int,
    rng: random.Random,
) -> _IsolationTreeNode:
    n = len(X)
    if current_height >= height_limit or n <= 1:
        return _IsolationTreeNode(size=n)

    num_features = len(X[0])
    feature_indices = list(range(num_features))
    rng.shuffle(feature_indices)

    for q in feature_indices:
        values = [row[q] for row in X]
        min_val, max_val = min(values), max(values)
        if min_val < max_val:
            p = rng.uniform(min_val, max_val)
            left_X = [row for row in X if row[q] < p]
            right_X = [row for row in X if row[q] >= p]
            return _IsolationTreeNode(
                left=_build_itree(left_X, current_height + 1, height_limit, rng),
                right=_build_itree(right_X, current_height + 1, height_limit, rng),
                split_feature=q,
                split_value=p,
                size=n,
            )

    return _IsolationTreeNode(size=n)


def _path_length(x: list[float], node: _IsolationTreeNode, current_depth: int = 0) -> float:
    if node.is_leaf:
        return current_depth + _c_factor(node.size)
    q = node.split_feature
    p = node.split_value
    if q is None or p is None:
        return current_depth + _c_factor(node.size)

    if x[q] < p:
        return _path_length(x, node.left, current_depth + 1)
    return _path_length(x, node.right, current_depth + 1)


class IsolationForestDetector:
    """Isolation Forest anomaly detector with calibrated 0-100 risk scoring."""

    MODEL_LABEL = "prototype Isolation Forest anomaly detector"

    def __init__(
        self,
        n_estimators: int = 50,
        max_samples: int = 256,
        anomaly_threshold: int = 65,
        seed: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.anomaly_threshold = anomaly_threshold
        self.seed = seed
        self.trees: list[_IsolationTreeNode] = []
        self.subsample_size = 0
        self.is_trained = False
        self.baseline_samples_count = 0

        # Automatic initialization on synthetic baseline data
        self.train_baseline()

    def generate_synthetic_baseline(self, count: int = 300) -> list[list[float]]:
        """Generate normal baseline traffic feature vectors."""
        rng = random.Random(self.seed)
        data: list[list[float]] = []
        for _ in range(count):
            # Normal operational characteristics: quiet periods to active normal workloads
            event_count = float(rng.randint(1, 30))
            failed_auth = float(rng.choice([0, 0, 0, 1, 1, 2]) if event_count > 2 else (1 if rng.random() < 0.25 else 0))
            fail_ratio = failed_auth / max(1.0, event_count)
            unique_ips = float(rng.randint(1, min(3, max(1, int(event_count)))))
            unique_users = float(rng.randint(1, min(3, max(1, int(event_count)))))
            unique_types = float(rng.randint(1, 3))
            auth_ratio = round(rng.uniform(0.2, 0.8), 4)
            access_ratio = round(rng.uniform(0.1, 0.5), 4)
            network_ratio = round(max(0.0, 1.0 - auth_ratio - access_ratio), 4)
            privileged_count = 0.0

            data.append([
                event_count,
                failed_auth,
                fail_ratio,
                unique_ips,
                unique_users,
                unique_types,
                auth_ratio,
                access_ratio,
                network_ratio,
                privileged_count,
            ])
        return data

    def train_baseline(self) -> None:
        """Fit Isolation Forest trees on synthetic normal baseline traffic."""
        baseline_data = self.generate_synthetic_baseline(300)
        rng = random.Random(self.seed)
        n = len(baseline_data)
        self.subsample_size = min(n, self.max_samples)
        height_limit = math.ceil(math.log2(max(self.subsample_size, 2)))

        self.trees = []
        for _ in range(self.n_estimators):
            subsample = rng.sample(baseline_data, self.subsample_size) if n > self.subsample_size else list(baseline_data)
            tree = _build_itree(subsample, 0, height_limit, rng)
            self.trees.append(tree)

        self.is_trained = True
        self.baseline_samples_count = n

    def predict(self, feature_vector: list[float]) -> dict[str, Any]:
        """Compute anomaly score and calibrated 0-100 risk score for a feature vector."""
        if not self.is_trained or not self.trees:
            self.train_baseline()

        avg_path = sum(_path_length(feature_vector, t) for t in self.trees) / len(self.trees)
        c = _c_factor(self.subsample_size)
        if c <= 0:
            raw_s = 0.5
        else:
            raw_s = 2.0 ** (-(avg_path / c))

        # Calibrate raw score s (where s in [0.45, 0.75]) into 0-100 risk score:
        calibrated = (raw_s - 0.46) / 0.22 * 100.0

        # Quiet / low-volume activity with minimal failures and no sudo is not an ML anomaly
        event_cnt = feature_vector[0] if len(feature_vector) > 0 else 0.0
        failed_cnt = feature_vector[1] if len(feature_vector) > 1 else 0.0
        priv_cnt = feature_vector[9] if len(feature_vector) > 9 else 0.0

        if event_cnt <= 5.0 and failed_cnt <= 2.0 and priv_cnt == 0.0:
            risk_score = int(max(0, min(40, round(calibrated * 0.5))))
        else:
            risk_score = int(max(0, min(100, round(calibrated))))

        # Anomaly flag
        is_anomaly = risk_score >= self.anomaly_threshold

        return {
            "raw_anomaly_score": round(raw_s, 4),
            "risk_score": risk_score,
            "is_anomaly": is_anomaly,
            "threshold": self.anomaly_threshold,
            "model": self.MODEL_LABEL,
        }

    def evaluate_event(
        self,
        session: Session,
        event: Event,
        window_seconds: int = 300,
    ) -> tuple[int, Alert | None]:
        """Extract sliding window features for an event, score anomaly risk, and emit Alert if anomalous."""
        feat_dict = extract_features_from_db(session, event, window_seconds=window_seconds)
        vec = vector_from_dict(feat_dict)
        pred = self.predict(vec)
        risk_score = pred["risk_score"]

        alert: Alert | None = None
        if pred["is_anomaly"]:
            severity = "CRITICAL" if risk_score >= 85 else ("HIGH" if risk_score >= 70 else "MEDIUM")
            alert_id = generate_next_alert_ids(session, count=1)[0]
            now = datetime.now(timezone.utc)
            alert = Alert(
                alert_id=alert_id,
                created_at=now,
                source="ml",
                severity=severity,
                title=f"Isolation Forest Anomaly Detected (Risk: {risk_score}/100)",
                message=(
                    f"Lightweight unsupervised Isolation Forest detector identified unusual behavior "
                    f"in sliding window (Risk Score: {risk_score}/100, raw score: {pred['raw_anomaly_score']})."
                ),
                event_id=event.event_id,
                incident_id=None,
                extras={
                    "model": self.MODEL_LABEL,
                    "risk_score": risk_score,
                    "raw_score": pred["raw_anomaly_score"],
                    "features": feat_dict,
                    "window_seconds": window_seconds,
                },
            )
            session.add(alert)
            session.flush()

        return risk_score, alert

    def get_status(self) -> dict[str, Any]:
        """Summary of detector configuration and health."""
        return {
            "model_name": self.MODEL_LABEL,
            "status": "ONLINE" if self.is_trained else "OFFLINE",
            "is_trained": self.is_trained,
            "n_estimators": self.n_estimators,
            "baseline_samples": self.baseline_samples_count,
            "anomaly_threshold": self.anomaly_threshold,
            "feature_names": FEATURE_NAMES,
            "score_scale": "0-100 risk score (not attack probability)",
        }


# Global singleton instance
default_ml_detector = IsolationForestDetector()
