"""
Kernel común de la plataforma multi-servicio.

Proporciona los contratos compartidos entre orquestador, agentes, tool
services y LLM gateway:

- ``events``         → esquemas de eventos + publicación/consumo (RabbitMQ)
- ``contracts``      → manifiesto de tools (descubrimiento) y envelope de respuestas
- ``tool_client``    → cliente con Tool Discovery (mapea manifiestos → endpoints)
- ``gateway_client`` → cliente del LLM Gateway
- ``task_store``     → metadatos de tarea en Redis (orquestador stateless)
- ``rpc``            → servidor RPC de eventos para tool services (modo asíncrono)

Depende solo de ``pika``, ``requests`` y ``redis`` (mínimo común denominador).
"""
from .contracts import (  # noqa: F401
    TOOL_MANIFEST_PATH,
    EnvelopeError,
    build_manifest,
    make_envelope,
    parse_envelope,
)
from .events import (  # noqa: F401
    AGENT_QUEUES,
    AGENT_RESULTS_QUEUE,
    AGENT_TASK_COMPLETED,
    AGENT_TASK_TRIGGERED,
    TASK_COMPLETED,
    TASK_RESULTS_QUEUE,
    TOOL_TASK_COMPLETED,
    TOOL_TASK_TRIGGERED,
    Event,
    EventConsumer,
    default_rabbit_params,
    publish_event,
    tool_rpc_queue,
)

__all__ = [
    "TOOL_MANIFEST_PATH",
    "EnvelopeError",
    "build_manifest",
    "make_envelope",
    "parse_envelope",
    "AGENT_QUEUES",
    "AGENT_RESULTS_QUEUE",
    "AGENT_TASK_COMPLETED",
    "AGENT_TASK_TRIGGERED",
    "TASK_COMPLETED",
    "TASK_RESULTS_QUEUE",
    "TOOL_TASK_COMPLETED",
    "TOOL_TASK_TRIGGERED",
    "Event",
    "EventConsumer",
    "default_rabbit_params",
    "publish_event",
    "tool_rpc_queue",
]
