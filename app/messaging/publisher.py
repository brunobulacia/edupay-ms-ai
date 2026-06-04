"""
Publica mensajes de respuesta de vuelta al API Gateway (Laravel) a través del
exchange 'edupay'.  Soporta dos patrones:

  1. RPC (reply_to + correlation_id): el gateway espera respuesta en una cola
     temporal que él mismo declara.
  2. Fire-and-forget con routing key fija: el gateway consume de una cola
     dedicada de respuestas.
"""
import json
import logging
from datetime import datetime, timezone

import aio_pika

from .connection import RabbitMQConnection, EXCHANGE_NAME

logger = logging.getLogger(__name__)


async def publish_response(
    payload: dict,
    routing_key: str,
    correlation_id: str | None = None,
    reply_to: str | None = None,
) -> None:
    """
    Publica *payload* como JSON en el exchange 'edupay'.

    - Si *reply_to* está presente (patrón RPC del gateway), el mensaje se
      envía directamente a esa cola temporal con el *correlation_id*.
    - Si no, se usa *routing_key* como destino normal.
    """
    channel = RabbitMQConnection.channel()

    body = json.dumps({
        **payload,
        "_publishedAt": datetime.now(timezone.utc).isoformat(),
        "_service": "ms-ia",
    }).encode()

    message = aio_pika.Message(
        body=body,
        content_type="application/json",
        correlation_id=correlation_id,
        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
    )

    if reply_to:
        # Patrón RPC: responder directamente a la cola temporal del gateway
        await channel.default_exchange.publish(message, routing_key=reply_to)
        logger.debug("[RabbitMQ] RPC reply → %s (corr=%s)", reply_to, correlation_id)
    else:
        exchange = await channel.get_exchange(EXCHANGE_NAME)
        await exchange.publish(message, routing_key=routing_key)
        logger.debug("[RabbitMQ] Published → %s", routing_key)
