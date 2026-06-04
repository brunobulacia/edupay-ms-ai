from motor.motor_asyncio import AsyncIOMotorDatabase


async def init_collections(db: AsyncIOMotorDatabase):
    existing = await db.list_collection_names()

    collections = [
        "predictions",
        "clusters",
        "ocr_analyses",
        "payment_events",
        "model_registry",
        "documents",
    ]

    for name in collections:
        if name not in existing:
            await db.create_collection(name)
            print(f"[DB] Created collection: {name}")
        else:
            print(f"[DB] Collection already exists: {name}")


async def init_indexes(db: AsyncIOMotorDatabase):
    # predictions
    await db.predictions.create_index([("familyId", 1), ("predictionDate", -1)])
    await db.predictions.create_index([("riskLevel", 1), ("predictionDate", -1)])

    # clusters
    await db.clusters.create_index([("familyId", 1)])
    await db.clusters.create_index([("clusterLabel", 1)])

    # ocr_analyses
    await db.ocr_analyses.create_index([("familyId", 1), ("createdAt", -1)])
    await db.ocr_analyses.create_index([("wasAcceptedByUser", 1)])

    # payment_events
    await db.payment_events.create_index([("familyId", 1), ("year", 1), ("month", 1)])
    await db.payment_events.create_index([("paidAt", -1)])

    # model_registry
    await db.model_registry.create_index([("modelName", 1), ("isProduction", 1)])

    # documents
    await db.documents.create_index([("familyId", 1)])
    await db.documents.create_index([("status", 1), ("uploadedAt", -1)])

    print("[DB] All indexes created.")


async def init_db(db: AsyncIOMotorDatabase):
    await init_collections(db)
    await init_indexes(db)
