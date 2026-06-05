"""
Conexión a DynamoDB usando boto3 (síncrono) envuelto con asyncio.to_thread.

En local apunta a DynamoDB Local (docker).
En producción apunta al endpoint real de AWS DynamoDB.
"""
import asyncio
import boto3
from boto3.dynamodb.conditions import Key, Attr  # noqa: F401 — re-exportados

from app.config.settings import settings

# ── Singletons ────────────────────────────────────────────────────────────────
_resource = None
_client   = None


def _build_kwargs() -> dict:
    kwargs: dict = {"region_name": settings.aws_region}
    if settings.dynamodb_endpoint_url:
        kwargs["endpoint_url"]          = settings.dynamodb_endpoint_url
        kwargs["aws_access_key_id"]     = "local"
        kwargs["aws_secret_access_key"] = "local"
    elif settings.aws_access_key_id and settings.aws_access_key_id != "local":
        kwargs["aws_access_key_id"]     = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return kwargs


def get_resource():
    global _resource
    if _resource is None:
        _resource = boto3.resource("dynamodb", **_build_kwargs())
    return _resource


def get_client():
    global _client
    if _client is None:
        _client = boto3.client("dynamodb", **_build_kwargs())
    return _client


def get_db():
    """Mantiene la misma firma que antes para compatibilidad."""
    return get_resource()


async def close_connection():
    pass  # boto3 no requiere cierre explícito


# ── Helpers async ─────────────────────────────────────────────────────────────

async def a_put_item(table_name: str, item: dict) -> None:
    table = get_resource().Table(table_name)
    await asyncio.to_thread(table.put_item, Item=item)


async def a_get_item(table_name: str, key: dict) -> dict | None:
    table = get_resource().Table(table_name)
    resp  = await asyncio.to_thread(table.get_item, Key=key)
    return resp.get("Item")


async def a_query(table_name: str, **kwargs) -> list[dict]:
    table = get_resource().Table(table_name)
    resp  = await asyncio.to_thread(table.query, **kwargs)
    return resp.get("Items", [])


async def a_scan(table_name: str, **kwargs) -> list[dict]:
    table = get_resource().Table(table_name)
    resp  = await asyncio.to_thread(table.scan, **kwargs)
    return resp.get("Items", [])


async def a_update_item(table_name: str, key: dict,
                        update_expression: str,
                        expression_values: dict,
                        expression_names: dict | None = None) -> None:
    table  = get_resource().Table(table_name)
    kw = {
        "Key":                       key,
        "UpdateExpression":          update_expression,
        "ExpressionAttributeValues": expression_values,
    }
    if expression_names:
        kw["ExpressionAttributeNames"] = expression_names
    await asyncio.to_thread(table.update_item, **kw)


async def a_list_tables() -> list[str]:
    client = get_client()
    resp   = await asyncio.to_thread(client.list_tables)
    return resp.get("TableNames", [])
