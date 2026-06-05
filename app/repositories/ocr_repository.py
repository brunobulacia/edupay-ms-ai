from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from app.database.connection import a_put_item, a_query
from app.database.dynamo_utils import to_dynamo, from_dynamo

TABLE = "edupay-ocr"


class OcrRepository:
    def __init__(self, db=None):
        pass

    async def save(self, doc: dict) -> str:
        now = datetime.now(timezone.utc).isoformat()
        item = to_dynamo(doc)
        item["familyId"]  = doc["familyId"]
        item["createdAt"] = doc.get("createdAt", datetime.now(timezone.utc)).isoformat() \
                            if hasattr(doc.get("createdAt"), "isoformat") else now
        await a_put_item(TABLE, item)
        return item["createdAt"]

    async def find_by_family(self, family_id: str, limit: int = 20) -> list[dict]:
        items = await a_query(
            TABLE,
            KeyConditionExpression=Key("familyId").eq(family_id),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [from_dynamo(i) for i in items]
