import json
from typing import Any, Dict

import pika

from app.config import settings


def publish_event(routing_key: str, payload: Dict[str, Any]) -> None:
    try:
        params = pika.URLParameters(settings.rabbitmq_url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.exchange_declare(exchange=settings.rabbitmq_exchange, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=settings.rabbitmq_exchange,
            routing_key=routing_key,
            body=json.dumps(payload, default=str),
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
        )
        connection.close()
    except Exception:
        # Notification delivery must not block account status updates.
        return None
