"""
Esquemas de eventos del bus y helpers de publicación/consumo (RabbitMQ).

Tipos de evento
---------------
- ``agent.task.triggered``  orquestador → agente   (dispara la ejecución)
- ``agent.task.completed``  agente → orquestador   (resultado del agente)
- ``tool.task.triggered``   agente → tool service  (invocación asíncrona / RPC)
- ``tool.task.completed``   tool service → agente  (respuesta asíncrona / RPC)
- ``task.completed``        orquestador → mundo    (pipeline completo)
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Optional

import pika

logger = logging.getLogger(__name__)

# ── Tipos de evento ────────────────────────────────────────────
AGENT_TASK_TRIGGERED = "agent.task.triggered"
AGENT_TASK_COMPLETED = "agent.task.completed"
TOOL_TASK_TRIGGERED = "tool.task.triggered"
TOOL_TASK_COMPLETED = "tool.task.completed"
TASK_COMPLETED = "task.completed"

# ── Colas ──────────────────────────────────────────────────────
AGENT_QUEUES = {
    "ideacion": "agent.ideacion.tasks",
    "publicacion": "agent.publicacion.tasks",
}
AGENT_RESULTS_QUEUE = "agent.results"      # agentes → orquestador
TASK_RESULTS_QUEUE = "task.results"        # orquestador → mundo


def tool_rpc_queue(tool_name: str) -> str:
    """Cola RPC de un tool service (modo asíncrono)."""
    return f"tool.{tool_name}.rpc"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ── Conexión ───────────────────────────────────────────────────
def default_rabbit_params() -> pika.ConnectionParameters:
    host = os.getenv("RABBITMQ_HOST", "localhost")
    user = os.getenv("RABBITMQ_USER", "user")
    password = os.getenv("RABBITMQ_PASS", "password")
    return pika.ConnectionParameters(
        host=host,
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        credentials=pika.PlainCredentials(user, password),
        heartbeat=30,
        blocked_connection_timeout=30,
    )


# ── Evento ─────────────────────────────────────────────────────
@dataclass
class Event:
    """Envelope estándar de cualquier evento del sistema."""

    event_type: str
    task_id: str
    correlation_id: str = ""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=_now)
    source: str = ""
    reply_to: Optional[str] = None
    agent: Optional[str] = None
    tool: Optional[str] = None
    operation: Optional[str] = None
    payload: dict = field(default_factory=dict)
    status: str = "completed"           # completed | failed
    error: Optional[str] = None
    duration_ms: Optional[int] = None

    def __post_init__(self) -> None:
        if not self.correlation_id:
            self.correlation_id = self.task_id

    def to_json(self) -> bytes:
        return json.dumps(asdict(self), ensure_ascii=False).encode("utf-8")

    @classmethod
    def from_body(cls, body: bytes | str) -> "Event":
        data = json.loads(body)
        if "event_type" in data:
            known = set(cls.__dataclass_fields__)
            return cls(**{k: v for k, v in data.items() if k in known})
        # JSON arbitrario (p.ej. un brief en bruto en ideation_queue)
        return cls(event_type="raw", task_id="", payload=data)

    @property
    def ok(self) -> bool:
        return self.status == "completed"


# ── Publicación ────────────────────────────────────────────────
def declare_queue(queue: str, durable: bool = True, params: pika.ConnectionParameters | None = None) -> None:
    conn = pika.BlockingConnection(params or default_rabbit_params())
    try:
        conn.channel().queue_declare(queue=queue, durable=durable)
    finally:
        conn.close()


def publish_event(
    queue: str,
    event: Event,
    *,
    durable: bool = True,
    params: pika.ConnectionParameters | None = None,
) -> None:
    """Publica un evento en ``queue`` (fiable: mensaje persistente)."""
    conn = pika.BlockingConnection(params or default_rabbit_params())
    try:
        ch = conn.channel()
        ch.queue_declare(queue=queue, durable=durable)
        ch.basic_publish(
            exchange="",
            routing_key=queue,
            body=event.to_json(),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                message_id=event.event_id,
                correlation_id=event.correlation_id,
            ),
        )
    finally:
        conn.close()


# ── Consumo ────────────────────────────────────────────────────
class EventConsumer:
    """Consumidor con reconexión automática (thread en segundo plano).

    ``handler(event, channel)`` recibe cada evento; si lanza excepción se
    registra y el mensaje (auto_ack=False + reject) no pierde la cola en
    bloques. Con ``auto_ack=True`` el mensaje se da por consumido.
    """

    def __init__(
        self,
        queue: str,
        handler: Callable[[Event], None],
        *,
        params: pika.ConnectionParameters | None = None,
        prefetch: int = 1,
        auto_ack: bool = True,
        name: str = "",
    ) -> None:
        self.queue = queue
        self.handler = handler
        self.params = params or default_rabbit_params()
        self.prefetch = prefetch
        self.auto_ack = auto_ack
        self.name = name or queue
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ── ciclo de vida ──
    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name=f"consumer-{self.name}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    # ── interno ──
    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                conn = pika.BlockingConnection(self.params)
                ch = conn.channel()
                ch.queue_declare(queue=self.queue, durable=True)
                ch.basic_qos(prefetch_count=self.prefetch)

                def _on_message(channel, method, properties, body):
                    try:
                        event = Event.from_body(body)
                        self.handler(event)
                        if not self.auto_ack:
                            channel.basic_ack(method.delivery_tag)
                    except Exception as exc:  # noqa: BLE001
                        logger.exception("[%s] error procesando evento: %s", self.name, exc)
                        if not self.auto_ack:
                            try:
                                channel.basic_nack(method.delivery_tag, requeue=True)
                            except Exception:  # noqa: BLE001
                                pass

                ch.basic_consume(queue=self.queue, on_message_callback=_on_message, auto_ack=self.auto_ack)
                logger.info("[%s] esperando eventos en '%s'", self.name, self.queue)
                ch.start_consuming()
            except pika.exceptions.AMQPConnectionError:
                if self._stop.is_set():
                    break
                logger.warning("[%s] RabbitMQ no disponible. Reintentando en 5 s …", self.name)
                self._stop.wait(5)
            except Exception as exc:  # noqa: BLE001
                if self._stop.is_set():
                    break
                logger.error("[%s] error inesperado: %s. Reintentando en 5 s …", self.name, exc)
                self._stop.wait(5)


# ── RPC sobre eventos (invocación asíncrona de tools) ─────────
def rpc_call(
    queue: str,
    event: Event,
    *,
    timeout: float = 30.0,
    params: pika.ConnectionParameters | None = None,
) -> Event:
    """Publica ``tool.task.triggered`` y espera ``tool.task.completed``.

    Crea una cola efímera de respuesta (``reply_to``) y hace polling hasta
    recibir el evento de vuelta o agotar el ``timeout``.
    """
    params = params or default_rabbit_params()
    reply_queue = f"rpc.{uuid.uuid4().hex[:16]}"
    event.reply_to = reply_queue
    if not event.event_type:
        event.event_type = TOOL_TASK_TRIGGERED

    conn = pika.BlockingConnection(params)
    try:
        ch = conn.channel()
        ch.queue_declare(queue=reply_queue, durable=False, exclusive=True, auto_delete=True)
        ch.queue_declare(queue=queue, durable=True)
        ch.basic_publish(
            exchange="",
            routing_key=queue,
            body=event.to_json(),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
                correlation_id=event.correlation_id,
                reply_to=reply_queue,
            ),
        )
        deadline = time.time() + timeout
        while time.time() < deadline:
            method, properties, body = ch.basic_get(queue=reply_queue, auto_ack=True)
            if method is not None:
                reply = Event.from_body(body)
                if reply.correlation_id == event.correlation_id:
                    return reply
            time.sleep(0.1)
        raise TimeoutError(f"Sin respuesta de '{queue}' en {timeout}s")
    finally:
        conn.close()
