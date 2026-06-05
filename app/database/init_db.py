"""
Crea las tablas DynamoDB si no existen. Idempotente.
"""
import asyncio
import logging

from app.database.connection import get_client

logger = logging.getLogger(__name__)

# ── Definición de tablas ──────────────────────────────────────────────────────
TABLE_DEFINITIONS = [
    {
        "TableName": "edupay-predictions",
        "KeySchema": [
            {"AttributeName": "familyId",       "KeyType": "HASH"},
            {"AttributeName": "predictionDate",  "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "familyId",       "AttributeType": "S"},
            {"AttributeName": "predictionDate", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        # Un solo ítem por familia (put_item reemplaza = upsert)
        "TableName": "edupay-clusters",
        "KeySchema": [
            {"AttributeName": "familyId", "KeyType": "HASH"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "familyId", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "edupay-ocr",
        "KeySchema": [
            {"AttributeName": "familyId",  "KeyType": "HASH"},
            {"AttributeName": "createdAt", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "familyId",  "AttributeType": "S"},
            {"AttributeName": "createdAt", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "edupay-payment-events",
        "KeySchema": [
            {"AttributeName": "familyId", "KeyType": "HASH"},
            {"AttributeName": "sk",       "KeyType": "RANGE"},  # paidAt#paymentId
        ],
        "AttributeDefinitions": [
            {"AttributeName": "familyId", "AttributeType": "S"},
            {"AttributeName": "sk",       "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "edupay-model-registry",
        "KeySchema": [
            {"AttributeName": "modelName", "KeyType": "HASH"},
            {"AttributeName": "version",   "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "modelName", "AttributeType": "S"},
            {"AttributeName": "version",   "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        # PK = docId (UUID). GSI permite buscar por familyId.
        "TableName": "edupay-documents",
        "KeySchema": [
            {"AttributeName": "docId",      "KeyType": "HASH"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "docId",      "AttributeType": "S"},
            {"AttributeName": "familyId",   "AttributeType": "S"},
            {"AttributeName": "uploadedAt", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "familyId-uploadedAt-index",
                "KeySchema": [
                    {"AttributeName": "familyId",   "KeyType": "HASH"},
                    {"AttributeName": "uploadedAt", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
]


async def init_db(db=None):  # db ignorado — mantenido por compatibilidad
    await _create_tables()


async def _create_tables():
    client   = get_client()
    existing = await asyncio.to_thread(client.list_tables)
    existing = existing.get("TableNames", [])

    for defn in TABLE_DEFINITIONS:
        name = defn["TableName"]
        if name not in existing:
            await asyncio.to_thread(client.create_table, **defn)
            logger.info("[DynamoDB] Tabla creada: %s", name)
        else:
            logger.info("[DynamoDB] Tabla ya existe: %s", name)
