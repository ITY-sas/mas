"""
Ejecutor de grafos de agente — patrón común a los agentes microservicio.

Garantiza semántica **idempotente at-least-once** sobre el bus de eventos:

1. El ``thread_id`` del checkpoint es ``{agente}:{task_id}``: cada tarea
   tiene su propio historial de estado en Redis.
2. Si la tarea ya terminó (checkpoint sin nodos pendientes y con
   resultados) → se reenvía el MISMO resultado sin re-ejecutar nada
   (reentrega de mensaje duplicado = no-op).
3. Si hay nodos pendientes (el proceso cayó a mitad) → se **retoma**
   desde el checkpoint (``invoke(None, config)``).
4. En caso contrario → ejecución nueva desde el estado inicial.

El estado intermedio del ciclo del agente vive en Redis, no en el proceso.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("agent_runner")


def run_agent_task(
    *,
    agent: str,
    task_id: str,
    graph: Any,
    initial_state: dict,
    extract: Callable[[dict], dict],
    is_done: Callable[[dict], bool],
    config_overrides: dict | None = None,
) -> dict:
    """Ejecuta (o retoma) el grafo del agente para ``task_id``.

    - ``extract(state)`` → dict de salida hacia el orquestador
      (p.ej. ``{"idea": ..., "idea_id": ...}``).
    - ``is_done(state)`` → True si el checkpoint ya contiene el resultado
      final (corta la reejecución en reentregas duplicadas).
    """
    config = {"configurable": {"thread_id": f"{agent}:{task_id}", **(config_overrides or {})}}

    snapshot = graph.get_state(config)
    values: dict = (snapshot.values if snapshot else {}) or {}

    if snapshot is not None and values and not getattr(snapshot, "next", ()) and is_done(values):
        logger.info("[%s] tarea %s ya completada (checkpoint) → reentrega idempotente",
                    agent, task_id)
        return extract(values)

    if snapshot is not None and getattr(snapshot, "next", ()):
        logger.info("[%s] tarea %s con nodos pendientes → retoma desde checkpoint",
                    agent, task_id)
        outcome = graph.invoke(None, config)
    else:
        logger.info("[%s] tarea %s → ejecución nueva", agent, task_id)
        outcome = graph.invoke(initial_state, config)

    return extract(outcome)
