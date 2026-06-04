from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.models.payment_event import PaymentEventIn
from app.repositories.payment_event_repository import PaymentEventRepository

router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/payment", status_code=201)
async def receive_payment_event(event: PaymentEventIn):
    doc = event.model_dump()
    doc["daysLate"] = event.days_late
    doc["createdAt"] = datetime.now(timezone.utc)

    await PaymentEventRepository(get_db()).save(doc)
    return {"status": "received", "familyId": event.familyId, "paymentId": event.paymentId}


@router.get("/payment/{family_id}")
async def get_payment_events(family_id: str, year: int | None = None):
    repo = PaymentEventRepository(get_db())
    if year:
        events = await repo.find_by_family_and_year(family_id, year)
    else:
        events = await repo.find_by_family(family_id)
    if not events:
        raise HTTPException(status_code=404, detail="No payment events found for this family")
    return {"familyId": family_id, "events": events}
