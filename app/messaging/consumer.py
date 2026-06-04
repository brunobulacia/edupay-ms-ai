"""
Consumer principal de RabbitMQ.

Escucha las colas declaradas en connection.py, despacha cada mensaje al
handler correspondiente y publica la respuesta de vuelta al API Gateway.

Patrón soportado: RPC (reply_to + correlation_id) y fire-and-forget.
"""
import asyncio
import json
import logging

import aio_pika
from aio_pika.abc import AbstractIncomingMessage

from .connection import (
    RabbitMQConnection,
    QUEUE_RISK_SCORE,
    QUEUE_CLUSTER,
    QUEUE_PAYMENT_EVENT,
    QUEUE_OCR,
    RK_RISK_SCORE_REPLY,
    RK_CLUSTER_REPLY,
    RK_PAYMENT_EVENT_REPLY,
    RK_OCR_REPLY,
)
from .publisher import publish_response
from .handlers import handle_risk_score, handle_cluster, handle_payment_event

logger = logging.getLogger(__name__)

_consumer_task: asyncio.Task | None = None


# ── Tabla de despacho ──────────────────────────────────────────────────────────
QUEUE_HANDLER_MAP = {
    QUEUE_RISK_SCORE:    (handle_risk_score,    RK_RISK_SCORE_REPLY),
    QUEUE_CLUSTER:       (handle_cluster,        RK_CLUSTER_REPLY),
    QUEUE_PAYMENT_EVENT: (handle_payment_event,  RK_PAYMENT_EVENT_REPLY),
    # OCR llega como binario (imagen) → no está soportado vía RabbitMQ por ahora
}


# ── Procesador genérico de mensajes ────────────────────────────────────────────

async def _process_message(
    message: AbstractIncomingMessage,
    handler,
    default_routing_key: str,
) -> None:
    async with message.process(requeue=True):
        try:
            payload = json.loads(message.body)
            logger.info(
                "[RabbitMQ] Received on queue=%s corr=%s",
                message.routing_key,
                message.correlation_id,
            )

            response = await handler(payload)

            await publish_response(
                payload=response,
                routing_key=default_routing_key,
                correlation_id=message.correlation_id,
                reply_to=message.reply_to,
            )

        except json.JSONDecodeError:
            logger.error("[RabbitMQ] Invalid JSON body — message discarded")
        except KeyError as exc:
            logger.error("[RabbitMQ] Missing field in payload: %s", exc)
            await publish_response(
                payload={"error": f"Missing field: {exc}"},
                routing_key=default_routing_key,
                correlation_id=message.correlation_id,
                reply_to=message.reply_to,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("[RabbitMQ] Unhandled error: %s", exc)
            await publish_response(
                payload={"error": str(exc)},
                routing_key=default_routing_key,
                correlation_id=message.correlation_id,
                reply_to=message.reply_to,
            )


# ── Inicio y parada ────────────────────────────────────────────────────────────

async def _run_consumers() -> None:
    channel = RabbitMQConnection.channel()

    for queue_name, (handler, reply_rk) in QUEUE_HANDLER_MAP.items():
        queue = await channel.get_queue(queue_name)
        await queue.consume(
            lambda msg, h=handler, rk=reply_rk: _process_message(msg, h, rk)
        )
        logger.info("[RabbitMQ] Consumer started for queue: %s", queue_name)

    logger.info("[RabbitMQ] All consumers running — waiting for messages…")
    await asyncio.Future()  # Bloquea hasta que la tarea sea cancelada


async def start_consumer() -> None:
    global _consumer_task
    _consumer_task = asyncio.create_task(_run_consumers())
    logger.info("[RabbitMQ] Consumer task created")


async def stop_consumer() -> None:
    global _consumer_task
    if _consumer_task and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
    logger.info("[RabbitMQ] Consumer task stopped")
