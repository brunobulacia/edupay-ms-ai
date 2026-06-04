"""
Gestión del ciclo de vida de la conexión a RabbitMQ.
Singleton asíncrono: una sola conexión + channel reutilizados por toda la app.
"""
import asyncio
import logging

import aio_pika
from aio_pika.abc import AbstractRobustConnection, AbstractChannel

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ── Exchange y colas declaradas por este microservicio ────────────────────────
EXCHANGE_NAME = "edupay"

# Colas que este ms-ia CONSUME (peticiones entrantes desde el API Gateway)
QUEUE_RISK_SCORE    = "ms_ia.risk_score"
QUEUE_CLUSTER       = "ms_ia.cluster"
QUEUE_PAYMENT_EVENT = "ms_ia.payment_event"
QUEUE_OCR           = "ms_ia.ocr"

# Routing keys que este ms-ia PUBLICA (respuestas hacia el API Gateway)
RK_RISK_SCORE_REPLY    = "gateway.ai.risk_score.reply"
RK_CLUSTER_REPLY       = "gateway.ai.cluster.reply"
RK_PAYMENT_EVENT_REPLY = "gateway.events.payment.reply"
RK_OCR_REPLY           = "gateway.ai.ocr.reply"


class RabbitMQConnection:
    """Singleton de conexión robusta a RabbitMQ."""

    _connection: AbstractRobustConnection | None = None
    _channel: AbstractChannel | None = None

    @classmethod
    async def connect(cls) -> None:
        cls._connection = await aio_pika.connect_robust(
            settings.rabbitmq_url,
            reconnect_interval=5,
        )
        cls._channel = await cls._connection.channel()
        await cls._channel.set_qos(prefetch_count=10)

        # Declara el exchange principal
        exchange = await cls._channel.declare_exchange(
            EXCHANGE_NAME,
            aio_pika.ExchangeType.TOPIC,
            durable=True,
        )

        # Declara y enlaza todas las colas consumidas
        for queue_name in (
            QUEUE_RISK_SCORE,
            QUEUE_CLUSTER,
            QUEUE_PAYMENT_EVENT,
            QUEUE_OCR,
        ):
            queue = await cls._channel.declare_queue(queue_name, durable=True)
            await queue.bind(exchange, routing_key=queue_name)
            logger.info("[RabbitMQ] Queue ready: %s", queue_name)

        logger.info("[RabbitMQ] Connected to %s", settings.rabbitmq_url.split("@")[-1])

    @classmethod
    async def close(cls) -> None:
        if cls._connection and not cls._connection.is_closed:
            await cls._connection.close()
            logger.info("[RabbitMQ] Connection closed")

    @classmethod
    def channel(cls) -> AbstractChannel:
        if cls._channel is None:
            raise RuntimeError("RabbitMQ channel not initialized. Call connect() first.")
        return cls._channel
