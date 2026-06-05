from boto3.dynamodb.conditions import Key

from app.database.connection import a_put_item, a_get_item
from app.database.dynamo_utils import to_dynamo, from_dynamo

TABLE = "edupay-clusters"


class ClusterRepository:
    def __init__(self, db=None):
        pass

    async def save(self, doc: dict) -> str:
        item = to_dynamo(doc)
        item["familyId"] = doc["familyId"]
        await a_put_item(TABLE, item)
        return doc["familyId"]

    async def find_by_family(self, family_id: str) -> dict | None:
        item = await a_get_item(TABLE, {"familyId": family_id})
        return from_dynamo(item) if item else None

    async def upsert(self, family_id: str, doc: dict) -> None:
        """En DynamoDB put_item reemplaza el item completo — equivale a upsert."""
        item = to_dynamo(doc)
        item["familyId"] = family_id
        await a_put_item(TABLE, item)
