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

    def start_idea_batch(
        self,
        *,
        client_id: int,
        brand_id: int,
        count: int,
        content: str = "",
        briefs: Optional[list[str]] = None,
        topics: Optional[list[str]] = None,
        content_format: str = "auto",
    ) -> dict:
        """Create a durable batch record and dispatch up to five idea tasks."""
        if not 1 <= count <= 5:
            raise ValueError("count debe estar entre 1 y 5")
        if briefs and len(briefs) > count:
            raise ValueError("no puede haber más briefs que ideas solicitadas")

        batch_id = str(uuid.uuid4())
        parent_brief = {
            "workflow": "idea_batch",
            "generation_batch_root": True,
            "generation_batch_id": batch_id,
            "generation_count": count,
            "brand_id": brand_id,
        }
        self.store.create(batch_id, brief=parent_brief, client_id=client_id)
        child_ids: list[str] = []
        angles = [
            "storytelling from the audience's point of view",
            "practical education and a useful takeaway",
            "a product demonstration grounded in a real use case",
            "community participation or a recognizable challenge",
            "a surprising contrast or myth-versus-fact narrative",
        ]

        for index in range(count):
            item_content = (briefs[index] if briefs and index < len(briefs) else content).strip()
            child_brief = {
                "workflow": "generate_idea",
                "client_id": client_id,
                "brand_id": brand_id,
                "content": item_content,
                "content_format": content_format,
                "topics": topics or [],
                "generation_batch_id": batch_id,
                "generation_index": index,
                "generation_count": count,
                "generation_angle": angles[index],
            }
            child_id = str(uuid.uuid4())
            child_ids.append(child_id)
            try:
                self.start_task(child_brief, client_id, task_id=child_id)
            except Exception as exc:  # noqa: BLE001
                if self.store.get(child_id) is None:
                    self.store.create(child_id, brief=child_brief, client_id=client_id)
                self.store.set_status(child_id, STATUS_FAILED, error=str(exc))

        self.store.update(batch_id, child_task_ids=child_ids)
        self._refresh_generation_batch(batch_id)
        return {
            "generation_batch_id": batch_id,
            "task_ids": child_ids,
            "count": count,
            "status": (self.store.get(batch_id) or {}).get("result", {}).get("status", STATUS_RUNNING),
        }

    def _refresh_generation_batch(self, batch_id: str) -> None:
        parent = self.store.get(batch_id)
        if not parent or not (parent.get("brief") or {}).get("generation_batch_root"):
            return
        children = self.store.list_by_generation_batch(batch_id)
        completed = sum(task.get("status") == STATUS_COMPLETED for task in children)
        failed = sum(task.get("status") == STATUS_FAILED for task in children)
        total = int((parent.get("brief") or {}).get("generation_count", len(children)))
        all_terminal = len(children) == total and completed + failed == total
        batch_status = (
            "failed" if all_terminal and completed == 0
            else "partial" if all_terminal and failed
            else "completed" if all_terminal
            else "running"
        )
        self.store.update(
            batch_id,
            status=STATUS_FAILED if batch_status == "failed" else (
                STATUS_COMPLETED if all_terminal else STATUS_RUNNING
            ),
            error="todas las ideas del lote fallaron" if batch_status == "failed" else None,
            result={
                "status": batch_status,
                "total": total,
                "completed": completed,
                "failed": failed,
                "task_ids": [task.get("task_id") for task in children],
            },
        )
        self.store.publish_update(batch_id, batch_status)

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
                batch_id = (task.get("brief") or {}).get("generation_batch_id")
                if batch_id:
                    self._refresh_generation_batch(batch_id)
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
                batch_id = (task.get("brief") or {}).get("generation_batch_id")
                if batch_id:
                    self._refresh_generation_batch(batch_id)
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
                "publication_variants": outcome.get("publication_variants", []),
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
        batch_id = (task.get("brief") or {}).get("generation_batch_id")
        if batch_id and not (task.get("brief") or {}).get("generation_batch_root"):
            self._refresh_generation_batch(batch_id)

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
