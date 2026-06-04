import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri, tlsCAFile=certifi.where())
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.mongodb_database]


async def close_connection():
    global _client
    if _client is not None:
        _client.close()
        _client = None
