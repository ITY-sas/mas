"""
Sistema multi-agente con LangGraph — orquestador stateless.

Contiene el esquema de estado del supervisor, el grafo de despacho con
``interrupt()`` (eventos RabbitMQ) y el runtime event-driven externo.
Los agentes de ideación/publicación son microservicios independientes;
las tools son microservicios independientes (Tools-as-a-Service).
"""
from .state import SupervisorState, initial_state
from .supervisor import (
    create_orchestrator,
    decide_next,
    dispatch_ideacion,
    dispatch_publicacion,
)
from .runtime import OrchestratorRuntime, build_checkpointer

__all__ = [
    "SupervisorState",
    "initial_state",
    "create_orchestrator",
    "decide_next",
    "dispatch_ideacion",
    "dispatch_publicacion",
    "OrchestratorRuntime",
    "build_checkpointer",
]
