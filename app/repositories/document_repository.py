import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key, Attr

from app.database.connection import a_put_item, a_query, a_scan, a_update_item
from app.database.dynamo_utils import to_dynamo, from_dynamo

TABLE = "edupay-documents"
GSI   = "familyId-uploadedAt-index"


class DocumentRepository:
    def __init__(self, db=None):
        pass

    async def save(self, doc: dict) -> str:
        doc_id     = str(uuid.uuid4())
        uploaded_at = doc.get("uploadedAt")
        uploaded_at_s = uploaded_at.isoformat() \
                        if hasattr(uploaded_at, "isoformat") \
                        else datetime.now(timezone.utc).isoformat()

        item = to_dynamo(doc)
        item["docId"]      = doc_id
        item["familyId"]   = doc["familyId"]
        item["uploadedAt"] = uploaded_at_s
        await a_put_item(TABLE, item)
        return doc_id

    async def find_by_family(self, family_id: str) -> list[dict]:
        items = await a_query(
            TABLE,
            IndexName=GSI,
            KeyConditionExpression=Key("familyId").eq(family_id),
            ScanIndexForward=False,
            Limit=50,
        )
        return [from_dynamo(i) for i in items]

    async def find_pending(self) -> list[dict]:
        items = await a_scan(
            TABLE,
            FilterExpression=Attr("status").eq("PENDING"),
        )
        return [from_dynamo(i) for i in items]

    async def update_status(self, doc_id: str, status: str,
                            reviewed_by: str, reason: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        expr   = "SET #st = :s, reviewedBy = :rb, reviewedAt = :ra"
        values = {":s": status, ":rb": reviewed_by, ":ra": now}
        names  = {"#st": "status"}
        if reason:
            expr  += ", rejectionReason = :rr"
            values[":rr"] = reason
        await a_update_item(TABLE, {"docId": doc_id},
                            expr, values, names)
