"""
Servidor RPC por eventos para tool services (modo asíncrono).

Un tool service puede atender invocaciones de dos formas:

- **REST** (síncrono, por defecto): ``GET /search?query=…``
- **Eventos** (tareas de larga duración): consume ``tool.task.triggered``
  en su cola y responde ``tool.task.completed`` a la cola ``reply_to``.

El wrapper gestiona: envelope de entrada/salida, duración, errores y
reconexión con RabbitMQ (mismo patrón que ``EventConsumer``).
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

import pika

from .events import (
    TOOL_TASK_COMPLETED,
    TOOL_TASK_TRIGGERED,
    Event,
    default_rabbit_params,
)

logger = logging.getLogger(__name__)

# handler(event) → dict con los datos de resultado (o lanza excepción)
ToolHandler = Callable[[Event], Any]


def handle_triggered_event(event: Event, handler: ToolHandler, source: str) -> Event:
    """Ejecuta un handler y construye el evento ``tool.task.completed``."""
    started = time.perf_counter()
    try:
        result = handler(event)
        status, error = "completed", None
        payload = {"result": result}
    except Exception as exc:  # noqa: BLE001
        logger.exception("[%s] handler falló: %s", source, exc)
        status, error = "failed", str(exc)
        payload = {}
    return Event(
        event_type=TOOL_TASK_COMPLETED,
        task_id=event.task_id,
        correlation_id=event.correlation_id,
        source=source,
        tool=event.tool,
        operation=event.operation,
        reply_to=None,
        payload=payload,
        status=status,
        error=error,
        duration_ms=int((time.perf_counter() - started) * 1000),
    )


def start_rpc_server(
    queue: str,
    handler: ToolHandler,
    *,
    source: str,
    params: Optional[pika.ConnectionParameters] = None,
    prefetch: int = 4,
) -> threading.Thread:
    """Arranca un consumidor RPC en hilo daemon con reconexión."""
    params = params or default_rabbit_params()
    stop = threading.Event()

    def _run() -> None:
        while not stop.is_set():
            try:
                conn = pika.BlockingConnection(params)
                ch = conn.channel()
                ch.queue_declare(queue=queue, durable=True)
                ch.basic_qos(prefetch_count=prefetch)

                def _on_message(channel, method, properties, body):
                    reply_to = properties.reply_to
                    try:
                        event = Event.from_body(body)
                        if event.event_type != TOOL_TASK_TRIGGERED:
                            logger.warning("[%s] evento inesperado: %s", source, event.event_type)
                        reply = handle_triggered_event(event, handler, source)
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("[%s] error procesando RPC", source)
                        reply = Event(
                            event_type=TOOL_TASK_COMPLETED,
                            task_id="",
                            source=source,
                            status="failed",
                            error=str(exc),
                        )
                    if reply_to:
                        channel.basic_publish(
                            exchange="",
                            routing_key=reply_to,
                            body=reply.to_json(),
                            properties=pika.BasicProperties(
                                delivery_mode=2, content_type="application/json"
                            ),
                        )
                    channel.basic_ack(method.delivery_tag)

                ch.basic_consume(queue=queue, on_message_callback=_on_message, auto_ack=False)
                logger.info("[%s] RPC escuchando en '%s'", source, queue)
                ch.start_consuming()
            except pika.exceptions.AMQPConnectionError:
                if stop.is_set():
                    break
                logger.warning("[%s] RabbitMQ no disponible. Reintentando en 5 s …", source)
                stop.wait(5)
            except Exception as exc:  # noqa: BLE001
                if stop.is_set():
                    break
                logger.error("[%s] error RPC: %s. Reintentando en 5 s …", source, exc)
                stop.wait(5)

    thread = threading.Thread(target=_run, name=f"rpc-{source}", daemon=True)
    thread.start()
    return thread


__all__ = ["start_rpc_server", "handle_triggered_event", "ToolHandler"]
