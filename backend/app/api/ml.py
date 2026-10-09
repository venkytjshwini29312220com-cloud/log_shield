"""API endpoints for Isolation Forest machine learning detector (Phase 6)."""

from typing import Any

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field

from app.detection import FEATURE_NAMES, default_ml_detector

router = APIRouter(prefix="/api/ml", tags=["ml"])


class MLScoreRequest(BaseModel):
    features: list[float] | None = None
    feature_dict: dict[str, float] | None = None


class MLScoreResponse(BaseModel):
    raw_anomaly_score: float
    risk_score: int
    is_anomaly: bool
    threshold: int
    model: str


@router.get("/status")
def get_ml_status() -> dict[str, Any]:
    """Retrieve status and metadata of the prototype Isolation Forest detector."""
    return default_ml_detector.get_status()


@router.post("/score", response_model=MLScoreResponse)
def score_features(payload: MLScoreRequest) -> MLScoreResponse:
    """Score a feature vector or named feature dictionary using the Isolation Forest model."""
    if payload.features is not None:
        if len(payload.features) != len(FEATURE_NAMES):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Expected {len(FEATURE_NAMES)} features: {FEATURE_NAMES}",
            )
        vector = payload.features
    elif payload.feature_dict is not None:
        vector = [payload.feature_dict.get(name, 0.0) for name in FEATURE_NAMES]
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either 'features' list or 'feature_dict' must be provided",
        )

    res = default_ml_detector.predict(vector)
    return MLScoreResponse(**res)
