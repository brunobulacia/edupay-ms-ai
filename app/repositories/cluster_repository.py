from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase


class ClusterRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["clusters"]

    async def save(self, doc: dict) -> str:
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def find_by_family(self, family_id: str) -> dict | None:
        return await self._col.find_one(
            {"familyId": family_id},
            {"_id": 0},
            sort=[("computedAt", -1)],
        )

    async def upsert(self, family_id: str, doc: dict) -> None:
        await self._col.update_one(
            {"familyId": family_id},
            {"$set": doc},
            upsert=True,
        )
