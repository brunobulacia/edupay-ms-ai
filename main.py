from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import logging

from fastapi import FastAPI
from app.database import get_db, close_connection, init_db
from app.routers.ai_router import router as ai_router
from app.routers.events_router import router as events_router
from app.routers.documents_router import router as documents_router
from app.messaging import start_consumer, stop_consumer
from app.messaging.connection import RabbitMQConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _register_models(db):
    models = [
        {
            "path": Path("models_store/mora_predictor/v1.0.0/meta.json"),
            "name": "mora_predictor",
            "algorithm": "LightGBM",
        },
        {
            "path": Path("models_store/family_clusterer/v1.0.0/meta.json"),
            "name": "family_clusterer",
            "algorithm": "KMeans",
        },
    ]
    for m in models:
        if not m["path"].exists():
            continue
        with open(m["path"]) as f:
            meta = json.load(f)
        await db.model_registry.update_one(
            {"modelName": m["name"], "version": meta["version"]},
            {"$set": {
                "modelName": m["name"],
                "version": meta["version"],
                "algorithm": m["algorithm"],
                "trainedAt": datetime.now(timezone.utc),
                "trainingSamples": meta.get("metrics", {}).get("trainingSamples", 5000),
                "metrics": meta.get("metrics", {}),
                "artifactS3Key": f"models/{m['name']}/{meta['version']}/model.pkl",
                "featuresUsed": meta.get("features", []),
                "isProduction": True,
            }},
            upsert=True,
        )
        print(f"[DB] model_registry updated: {m['name']} {meta['version']}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # ── Base de datos ──────────────────────────────────────────────────────────
    db = get_db()
    await init_db(db)
    await _register_models(db)

    # ── RabbitMQ ───────────────────────────────────────────────────────────────
    try:
        await RabbitMQConnection.connect()
        await start_consumer()
        logger.info("[App] RabbitMQ consumer started")
    except Exception as exc:  # noqa: BLE001
        logger.warning("[App] RabbitMQ not available — running HTTP-only mode: %s", exc)

    yield

    # ── Cleanup ────────────────────────────────────────────────────────────────
    await stop_consumer()
    await RabbitMQConnection.close()
    await close_connection()


app = FastAPI(title="MS-IA — EduPay", version="1.0.0", lifespan=lifespan)

app.include_router(ai_router)
app.include_router(events_router)
app.include_router(documents_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ms-ia"}
