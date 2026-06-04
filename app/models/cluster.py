from pydantic import BaseModel, Field
from typing import Literal


class ClusterFeatures(BaseModel):
    avg_payment_day: float = Field(10.0, ge=1, le=31)
    std_dev_payment_day: float = Field(2.0, ge=0)
    mora_incidence: float = Field(0.0, ge=0, le=1)
    annual_payer_score: float = Field(0.0, ge=0, le=1)
    method_consistency: float = Field(1.0, ge=0, le=1)
    months_active: int = Field(12, ge=1)


class ClusterResponse(BaseModel):
    familyId: str
    cluster: int
    clusterLabel: Literal["PUNTUAL_ESTRELLA", "REGULAR", "IRREGULAR", "MOROSO_CRONICO"]
    recommendedAction: str
    modelVersion: str
    features: dict
    computedAt: str
