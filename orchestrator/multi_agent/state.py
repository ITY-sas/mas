"""
Esquema de estado del supervisor (orquestador stateless).

El estado global del pipeline se persiste EXTERNAMENTE:

- **Ciclo de planificación / dispatch** → checkpoints de LangGraph en Redis
  (``RedisSaver`` con ``thread_id = task_id``).
- **Metadatos y resultados** → ``common.task_store.TaskStore`` (Redis).
- **Historial de chat** → PostgreSQL (``orchestrator.history``).

El proceso del orquestador no mantiene estado entre peticiones: puede
reiniciarse o escalar horizontalmente sin perder el ciclo en curso.
"""
from typing import Annotated, TypedDict

import operator


class SupervisorState(TypedDict):
    """Estado global compartido por todo el ciclo supervisor → agentes.

    El supervisor lee esto para decidir qué microservicio de agente
    invocar a continuación; los agentes devuelven sus resultados vía
    ``agent.task.completed`` y se inyectan con ``Command(resume=...)``.
    """

    # ── Entrada ──
    brief: dict
    client_id: int

    # ── Resultado del agente de ideación ──
    idea: str
    idea_id: int

    # ── Resultado del agente de publicación ──
    publication: str
    publication_id: int

    # ── Registro de auditoría (append-only vía operator.add) ──
    log: Annotated[list[str], operator.add]


def initial_state(brief: dict, client_id: int) -> SupervisorState:
    """Estado inicial para una tarea nueva."""
    return {
        "brief": brief,
        "client_id": client_id,
        "idea": "",
        "idea_id": 0,
        "publication": "",
        "publication_id": 0,
        "log": [],
    }
