from motor.motor_asyncio import AsyncIOMotorDatabase


class DocumentRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["documents"]

    async def save(self, doc: dict) -> str:
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def find_by_family(self, family_id: str) -> list[dict]:
        cursor = self._col.find(
            {"familyId": family_id},
            {"_id": 0},
            sort=[("uploadedAt", -1)],
        )
        return await cursor.to_list(length=50)

    async def find_pending(self) -> list[dict]:
        cursor = self._col.find(
            {"status": "PENDING"},
            {"_id": 0},
            sort=[("uploadedAt", -1)],
        )
        return await cursor.to_list(length=100)

    async def update_status(self, doc_id: str, status: str, reviewed_by: str, reason: str | None = None) -> None:
        from datetime import datetime, timezone
        from bson import ObjectId
        await self._col.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {
                "status": status,
                "reviewedBy": reviewed_by,
                "reviewedAt": datetime.now(timezone.utc),
                "rejectionReason": reason,
            }},
        )
