from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key, Attr

from app.database.connection import a_put_item, a_query
from app.database.dynamo_utils import to_dynamo, from_dynamo

TABLE = "edupay-payment-events"


class PaymentEventRepository:
    def __init__(self, db=None):
        pass

    async def save(self, doc: dict) -> str:
        paid_at   = doc.get("paidAt")
        paid_at_s = paid_at.isoformat() if hasattr(paid_at, "isoformat") else str(paid_at)
        payment_id = doc.get("paymentId", "unknown")
        sk = f"{paid_at_s}#{payment_id}"

        item = to_dynamo(doc)
        item["familyId"] = doc["familyId"]
        item["sk"]       = sk
        # Guardar campos planos para búsqueda
        item["paidAt"]    = paid_at_s
        item["paymentId"] = payment_id
        await a_put_item(TABLE, item)
        return sk

    async def find_by_family(self, family_id: str, limit: int = 24) -> list[dict]:
        items = await a_query(
            TABLE,
            KeyConditionExpression=Key("familyId").eq(family_id),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [from_dynamo(i) for i in items]

    async def find_by_family_and_year(self, family_id: str, year: int) -> list[dict]:
        items = await a_query(
            TABLE,
            KeyConditionExpression=Key("familyId").eq(family_id),
            FilterExpression=Attr("year").eq(year),
            ScanIndexForward=True,
        )
        return [from_dynamo(i) for i in items]
