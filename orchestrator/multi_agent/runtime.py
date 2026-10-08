"""
Runtime event-driven del orquestador stateless.

Máquina de estados externa del pipeline::

    POST /process
        → TaskStore.create(task_id)                 (Redis)
        → graph.invoke(initial, thread_id=task)     → hasta primer interrupt()
        → publica agent.task.triggered              (RabbitMQ)
        ⇠ consumidor recibe agent.task.completed
        → graph.invoke(Command(resume=result))      → siguiente interrupt o END
        → ...hasta END...
        → guarda historial de chat                  (PostgreSQL)
        → publica task.completed                    (RabbitMQ)

Toda la memoria vive en Redis (checkpoints LangGraph + metadatos de tarea).
El proceso puede morir en cualquier punto: al arrancar,
:meth:`OrchestratorRuntime.recover_running_tasks` retoma las tareas
pendientes publicando de nuevo su ``agent.task.triggered`` pendiente
(semántica *at-least-once*; los agentes deben ser idempotentes).
"""
from __future__ import annotations

import logging
import os
import threading
import time
import uuid
from typing import Optional

from langgraph.checkpoint.redis import RedisSaver
from langgraph.types import Command

from common.events import (
    AGENT_RESULTS_QUEUE,
    AGENT_TASK_COMPLETED,
    AGENT_TASK_TRIGGERED,
    TASK_COMPLETED,
    TASK_RESULTS_QUEUE,
    Event,
    EventConsumer,
    publish_event,
)
from common.task_store import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_RUNNING,
    TaskStore,
)

from .supervisor import create_orchestrator
from .state import initial_state

logger = logging.getLogger("orchestrator.runtime")

DEFAULT_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


def build_checkpointer(redis_url: Optional[str] = None) -> RedisSaver:
    """Checkpointer LangGraph sobre Redis (ciclo de planificación externo)."""
    saver = RedisSaver(redis_url or DEFAULT_REDIS_URL)
    saver.setup()  # crea índices (requiere Redis Stack: RedisJSON + RediSearch)
    return saver


class OrchestratorRuntime:
    """Coordina agentes vía eventos manteniendo el proceso stateless."""

    def __init__(
        self,
        store: Optional[TaskStore] = None,
        checkpointer: Optional[RedisSaver] = None,
        history_add: Optional[callable] = None,
    ) -> None:
        self.store = store or TaskStore()
        self.checkpointer = checkpointer or build_checkpointer()
        self.graph = create_orchestrator(self.checkpointer)
        # historial de chat: callable inyectado o import perezoso de history.py
        self._history_add_fn = history_add
        self._lock = threading.Lock()  # serializa reanudaciones por seguridad

    # ── utilidades ─────────────────────────────────────────────
    @staticmethod
    def _config(task_id: str) -> dict:
        return {"configurable": {"thread_id": task_id}}

    # ── arranque de tarea ──────────────────────────────────────
    def start_task(self, brief: dict, client_id: int, task_id: str = "") -> str:
        """Crea la tarea, arranca el grafo hasta el 1er interrupt y despacha."""
        task_id = task_id or str(uuid.uuid4())
        self.store.create(task_id, brief=brief, client_id=client_id)
        self._save_chat(task_id, client_id, "user",
                        f"[client_id={client_id}] {brief.get('content', '')}")
        logger.info("━" * 60)
        logger.info("tarea %s creada (client_id=%s)", task_id, client_id)

        outcome = self.graph.invoke(initial_state(brief, client_id), self._config(task_id))
        self._advance(task_id, outcome)
        return task_id

    # ── avance del ciclo (interrupción → evento → reanudación) ─
    def _advance(self, task_id: str, outcome: dict) -> None:
        interrupts = outcome.get("__interrupt__") or ()
        if not interrupts:
            self._finalize(task_id, outcome)
            return
        iv = interrupts[0].value
        agent = iv.get("agent")
        queue = iv.get("queue")
        payload = iv.get("payload") or {}
        # Guardamos el despacho pendiente → permite recuperación tras caída
        self.store.update(task_id, pending={"agent": agent, "queue": queue, "payload": payload})
        try:
            self._dispatch_pending(task_id, {"agent": agent, "queue": queue, "payload": payload})
        except Exception as exc:  # noqa: BLE001
            logger.error("tarea %s: no se pudo publicar el despacho: %s", task_id, exc)
            self.store.set_status(task_id, STATUS_FAILED, error=f"sin broker: {exc}")
            raise

    def _dispatch_pending(self, task_id: str, pending: dict) -> None:
        """Re-publica el despacho pendiente (recuperación / reintentos)."""
        publish_event(
            pending["queue"],
            Event(
                event_type=AGENT_TASK_TRIGGERED,
                task_id=task_id,
                correlation_id=task_id,
                source="orchestrator",
                agent=pending.get("agent"),
                payload=pending.get("payload") or {},
            ),
        )
        logger.info("tarea %s → agent.task.triggered [%s]", task_id, pending.get("agent"))

    # ── llegada de agent.task.completed ────────────────────────
    def on_agent_completed(self, event: Event) -> None:
        task_id, agent = event.task_id, event.agent or "?"
        if event.event_type not in (AGENT_TASK_COMPLETED, "raw"):
            logger.warning("evento inesperado en '%s': %s", AGENT_RESULTS_QUEUE, event.event_type)
            return
        with self._lock:
            task = self.store.get(task_id)
            if task is None:
                logger.warning("resultado de agente para tarea desconocida %s", task_id)
                return
            if task.get("status") != STATUS_RUNNING:
                logger.info("tarea %s ya finalizada; se ignora resultado de %s",
                            task_id, agent)
                return

            if not event.ok:
                logger.error("tarea %s ← agent.task.completed FAILED (%s): %s",
                             task_id, agent, event.error)
                self.store.set_status(task_id, STATUS_FAILED, error=event.error)
                self._save_chat(task_id, task.get("client_id"), "assistant",
                                f"[ERROR en agente {agent}] {event.error}")
                return

            # Guarda anti-duplicados: sólo avanza el agente que se está
            # esperando (reentregas o resultados obsoletos se ignoran).
            pending = task.get("pending") or {}
            expected = pending.get("agent")
            if expected and expected != agent:
                logger.info(
                    "tarea %s: resultado de '%s' no esperado (esperando '%s') "
                    "→ ignorado", task_id, agent, expected,
                )
                return

            result = event.payload.get("result") or {}
            self.store.record_agent_result(task_id, agent, result)
            logger.info("tarea %s ← agent.task.completed [%s] %s",
                        task_id, agent, event.duration_ms)

            try:
                outcome = self.graph.invoke(Command(resume=result), self._config(task_id))
            except Exception as exc:  # noqa: BLE001
                logger.exception("tarea %s: fallo reanudando el grafo", task_id)
                self.store.set_status(task_id, STATUS_FAILED, error=str(exc))
                return
            self._advance(task_id, outcome)

    # ── finalización ───────────────────────────────────────────
    def _finalize(self, task_id: str, outcome: dict) -> None:
        task = self.store.update(
            task_id,
            status=STATUS_COMPLETED,
            error=None,
            pending=None,
            result={
                "idea": outcome.get("idea", ""),
                "idea_id": outcome.get("idea_id", 0),
                "preproduction": outcome.get("preproduction", {}),
                "publication": outcome.get("publication", ""),
                "publication_id": outcome.get("publication_id", 0),
                "postiz": outcome.get("postiz", {}),
            },
        )
        logger.info(
            "tarea %s COMPLETADA idea_id=%s publication_id=%s",
            task_id, outcome.get("idea_id"), outcome.get("publication_id"),
        )
        assistant_msg = (
            f"IDEA (id={outcome.get('idea_id')}):\n{outcome.get('idea', '')}\n\n"
            f"PUBLICACIÓN (id={outcome.get('publication_id')}):\n"
            f"{outcome.get('publication', '')}"
        )
        self._save_chat(task_id, task.get("client_id"), "assistant", assistant_msg)
        # Evento de salida: pipeline completo
        try:
            publish_event(
                TASK_RESULTS_QUEUE,
                Event(
                    event_type=TASK_COMPLETED,
                    task_id=task_id,
                    correlation_id=task_id,
                    source="orchestrator",
                    payload={"result": task.get("result") or {}},
                    duration_ms=int(
                        (time.time() - (task.get("created_at") or time.time())) * 1000
                    ),
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("no se pudo publicar task.completed: %s", exc)
        self.store.publish_update(task_id, STATUS_COMPLETED)

    # ── historial de chat (PostgreSQL) ─────────────────────────
    def _resolve_history_fn(self):
        if self._history_add_fn is not None:
            return self._history_add_fn
        import importlib

        for module in ("history", "orchestrator.history"):
            try:
                mod = importlib.import_module(module)
                self._history_add_fn = getattr(mod, "add_message")
                return self._history_add_fn
            except (ImportError, AttributeError):
                continue
        logger.warning("módulo de historial de chat no disponible")
        return None

    def _save_chat(self, task_id: str, client_id: object, role: str, content: str) -> None:
        add = self._resolve_history_fn()
        if add is None:
            return
        try:
            add(task_id, client_id, role, content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("historial de chat no guardado: %s", exc)

    # ── consumidor de resultados de agentes ────────────────────
    def start_consumers(self) -> None:
        """Arranca el consumidor de ``agent.task.completed`` (hilo daemon).

        Cada evento recibido reanuda el grafo supervisor desde el
        checkpoint de Redis (el proceso no retiene estado).
        """
        if getattr(self, "_consumer", None) is not None:
            return
        self._consumer = EventConsumer(
            AGENT_RESULTS_QUEUE, self.on_agent_completed, name="agent-results"
        )
        self._consumer.start()
        logger.info("consumidor de '%s' iniciado", AGENT_RESULTS_QUEUE)

    # ── recuperación tras caída ────────────────────────────────
    def recover_running_tasks(self) -> int:
        """Re-publica los despachos pendientes de tareas no finalizadas."""
        recovered = 0
        for task in self.store.list_by_status(STATUS_RUNNING):
            pending = task.get("pending")
            task_id = task.get("task_id")
            if not pending or not task_id:
                continue
            try:
                self._dispatch_pending(task_id, pending)
                recovered += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("recuperación falló para %s: %s", task_id, exc)
        if recovered:
            logger.info("recuperadas %d tarea(s) pendiente(s)", recovered)
        return recovered


__all__ = ["OrchestratorRuntime", "build_checkpointer"]
