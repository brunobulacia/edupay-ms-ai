import time
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key

from app.database.connection import a_put_item, a_query
from app.database.dynamo_utils import to_dynamo, from_dynamo

TABLE = "edupay-predictions"


class PredictionRepository:
    def __init__(self, db=None):  # db ignorado — boto3 usa cliente global
        pass

    async def save(self, prediction: dict) -> str:
        # SK único: predictionDate#epoch_ms
        epoch = int(time.time() * 1000)
        date  = prediction.get("predictionDate", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        sk    = f"{date}#{epoch}"

        item = to_dynamo({**prediction, "predictionDate": sk})
        item["familyId"]       = prediction["familyId"]
        item["predictionDate"] = sk
        await a_put_item(TABLE, item)
        return sk

    async def find_by_family(self, family_id: str) -> list[dict]:
        items = await a_query(
            TABLE,
            KeyConditionExpression=Key("familyId").eq(family_id),
            ScanIndexForward=False,
            Limit=12,
        )
        return [from_dynamo(i) for i in items]

    async def find_latest(self, family_id: str) -> dict | None:
        items = await a_query(
            TABLE,
            KeyConditionExpression=Key("familyId").eq(family_id),
            ScanIndexForward=False,
            Limit=1,
        )
        return from_dynamo(items[0]) if items else None
