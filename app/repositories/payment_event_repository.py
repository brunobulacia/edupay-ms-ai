from motor.motor_asyncio import AsyncIOMotorDatabase


class PaymentEventRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["payment_events"]

    async def save(self, doc: dict) -> str:
        result = await self._col.insert_one(doc)
        return str(result.inserted_id)

    async def find_by_family(self, family_id: str, limit: int = 24) -> list[dict]:
        cursor = self._col.find(
            {"familyId": family_id},
            {"_id": 0},
            sort=[("paidAt", -1)],
            limit=limit,
        )
        return await cursor.to_list(length=limit)

    async def find_by_family_and_year(self, family_id: str, year: int) -> list[dict]:
        cursor = self._col.find(
            {"familyId": family_id, "year": year},
            {"_id": 0},
            sort=[("month", 1)],
        )
        return await cursor.to_list(length=12)
