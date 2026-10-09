"""Risk scoring API endpoints for LogShield (Phase 8)."""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import RiskCalculateRequest, RiskCalculateResponse, RiskWeightsResponse
from app.risk.engine import default_risk_engine

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get(
    "/weights",
    response_model=RiskWeightsResponse,
    summary="Get risk engine component weights and severity bands",
)
def get_risk_weights() -> RiskWeightsResponse:
    """Returns the current configurable weights and severity thresholds for the risk engine."""
    return RiskWeightsResponse(
        weights=default_risk_engine.get_weights(),
        severity_bands={
            "LOW": "0–30",
            "MEDIUM": "31–60",
            "HIGH": "61–80",
            "CRITICAL": "81–100",
        },
        formula="risk = round(100 * (w_rule * rule_score + w_ml * ml_score + w_corr * correlation_score + w_beh * behavioral_score))",
    )


@router.post(
    "/calculate",
    response_model=RiskCalculateResponse,
    summary="Simulate / calculate composite risk score and breakdown",
)
def calculate_risk(request: RiskCalculateRequest) -> RiskCalculateResponse:
    """Compute composite risk score and contribution breakdown from component scores."""
    custom_w = request.custom_weights or {}
    w_rule = custom_w.get("rule")
    w_ml = custom_w.get("ml")
    w_corr = custom_w.get("correlation")
    w_beh = custom_w.get("behavioral")

    # If custom weights are provided, validate they roughly sum to 1.0
    if request.custom_weights is not None:
        total_w = sum(request.custom_weights.values())
        if abs(total_w - 1.0) > 0.05:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Custom weights must sum to approximately 1.0 (got {total_w})",
            )

    composite, severity, breakdown = default_risk_engine.compute_composite_score(
        rule_score=request.rule_score,
        ml_score=request.ml_score,
        correlation_score=request.correlation_score,
        behavioral_score=request.behavioral_score,
        w_rule=w_rule,
        w_ml=w_ml,
        w_corr=w_corr,
        w_beh=w_beh,
    )

    return RiskCalculateResponse(
        composite_score=composite,
        severity=severity,
        weights=breakdown["weights"],
        components=breakdown["components"],
        contributions=breakdown["contributions"],
        display_label=f"Risk Score: {composite}/100 ({severity})",
    )
