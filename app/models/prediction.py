from pydantic import BaseModel, Field
from typing import Literal


class PredictionFeatures(BaseModel):
    avg_days_late_last_3_months: float = Field(0.0, ge=-15, le=60)
    max_days_late_ever: float = Field(0.0, ge=-15, le=120)
    months_paid_on_time_ratio: float = Field(1.0, ge=0, le=1)
    consecutive_late_payments: int = Field(0, ge=0)
    has_paid_annual_ever: bool = False
    preferred_payment_method_qr: bool = False
    preferred_payment_method_stripe: bool = True
    preferred_payment_method_blockchain: bool = False
    avg_payment_day_of_month: float = Field(10.0, ge=1, le=31)
    uses_mobile_app: bool = True
    num_students: int = Field(1, ge=1)
    years_enrolled: int = Field(1, ge=0)
    has_discount: bool = False
    month: int = Field(1, ge=1, le=12)
    is_after_carnaval: bool = False
    months_remaining_year: int = Field(11, ge=0, le=11)


class RiskScoreResponse(BaseModel):
    familyId: str
    riskScore: float
    riskLevel: Literal["LOW", "MEDIUM", "HIGH"]
    modelVersion: str
    features: dict
    predictionDate: str
