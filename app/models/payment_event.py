from pydantic import BaseModel, Field
from typing import Literal
from datetime import datetime


class PaymentEventIn(BaseModel):
    familyId: str
    studentId: str
    paymentId: str
    eventType: Literal["payment.confirmed", "payment.failed", "payment.refunded"]
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2020)
    method: Literal["QR", "STRIPE", "BLOCKCHAIN"]
    amountBOB: float = Field(..., gt=0)
    paidAt: datetime
    dueDate: datetime

    @property
    def days_late(self) -> int:
        delta = self.paidAt - self.dueDate
        return delta.days
