from motor.motor_asyncio import AsyncIOMotorDatabase


class OcrRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["ocr_analyses"]

    async def save(self, doc: dict) -> str:
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def find_by_family(self, family_id: str, limit: int = 20) -> list[dict]:
        cursor = self._col.find(
            {"familyId": family_id},
            {"_id": 0},
            sort=[("createdAt", -1)],
            limit=limit,
        )
        return await cursor.to_list(length=limit)
