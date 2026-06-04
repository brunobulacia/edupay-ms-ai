from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase


class PredictionRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["predictions"]

    async def save(self, prediction: dict) -> str:
        result = await self._col.insert_one(prediction)
        return str(result.inserted_id)

    async def find_by_family(self, family_id: str) -> list[dict]:
        cursor = self._col.find(
            {"familyId": family_id},
            {"_id": 0},
            sort=[("predictionDate", -1)],
            limit=12,
        )
        return await cursor.to_list(length=12)

    async def find_latest(self, family_id: str) -> dict | None:
        return await self._col.find_one(
            {"familyId": family_id},
            {"_id": 0},
            sort=[("predictionDate", -1)],
        )
