"""
Almacén de estado de tareas en Redis (orquestador **stateless**).

El orquestador no guarda nada en memoria entre peticiones:

- **Ciclo de planificación / dispatch** → checkpoints de LangGraph en Redis
  (``RedisSaver``, ``thread_id = task_id``).
- **Metadatos de tarea y resultados** → este ``TaskStore`` (JSON en Redis).
- **Historial de chat durable** → PostgreSQL (fuera de este módulo).
"""
from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)

TASK_PREFIX = "task:"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

# pub/sub para esperas eficientes (en lugar de sólo polling)
CHANNEL_PREFIX = "task.channel:"


def default_redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://localhost:6379")


class TaskStore:
    """Metadatos de tarea + resultados de agentes en Redis."""

    def __init__(self, redis_url: Optional[str] = None, client: Any = None) -> None:
        if client is not None:
            self.r = client
        else:
            import redis  # importación perezosa (sólo quien lo use)

            self.r = redis.Redis.from_url(redis_url or default_redis_url(), decode_responses=True)

    # ── CRUD básico ────────────────────────────────────────────
    @staticmethod
    def _key(task_id: str) -> str:
        return f"{TASK_PREFIX}{task_id}"

    @staticmethod
    def new_task_id() -> str:
        return str(uuid.uuid4())

    def create(self, task_id: str, *, brief: dict, client_id: int) -> dict:
        task = {
            "task_id": task_id,
            "correlation_id": task_id,
            "status": STATUS_RUNNING,
            "error": None,
            "client_id": client_id,
            "brief": brief,
            "agents": {},
            "result": {},
            "created_at": time.time(),
            "updated_at": time.time(),
        }
        self.r.set(self._key(task_id), json.dumps(task, ensure_ascii=False))
        return task

    def get(self, task_id: str) -> Optional[dict]:
        raw = self.r.get(self._key(task_id))
        return json.loads(raw) if raw else None

    def update(self, task_id: str, **fields: Any) -> dict:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"tarea desconocida: {task_id}")
        task.update(fields)
        task["updated_at"] = time.time()
        self.r.set(self._key(task_id), json.dumps(task, ensure_ascii=False))
        return task

    def set_status(self, task_id: str, status: str, *, error: Optional[str] = None) -> dict:
        return self.update(task_id, status=status, error=error)

    def record_agent_result(self, task_id: str, agent: str, result: dict,
                            *, status: str = STATUS_COMPLETED,
                            error: Optional[str] = None) -> dict:
        """Guarda el resultado de un agente y lo refleja en ``result``."""
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"tarea desconocida: {task_id}")
        task.setdefault("agents", {})[agent] = {
            "status": status,
            "error": error,
            "result": result,
            "at": time.time(),
        }
        task.setdefault("result", {}).update(result)
        task["updated_at"] = time.time()
        self.r.set(self._key(task_id), json.dumps(task, ensure_ascii=False))
        self.publish_update(task_id, status)
        return task

    # ── Listados / recuperación ────────────────────────────────
    def list_by_status(self, status: str, *, limit: int = 100) -> list[dict]:
        tasks = []
        for key in self.r.scan_iter(match=f"{TASK_PREFIX}*", count=200):
            raw = self.r.get(key)
            if not raw:
                continue
            try:
                task = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if task.get("status") == status:
                tasks.append(task)
            if len(tasks) >= limit:
                break
        return tasks

    def list_by_generation_batch(self, batch_id: str) -> list[dict]:
        """Return child generation tasks ordered by their requested position."""
        tasks = []
        for key in self.r.scan_iter(match=f"{TASK_PREFIX}*", count=200):
            raw = self.r.get(key)
            if not raw:
                continue
            try:
                task = json.loads(raw)
            except json.JSONDecodeError:
                continue
            brief = task.get("brief") or {}
            if (
                brief.get("generation_batch_id") == batch_id
                and not brief.get("generation_batch_root")
            ):
                tasks.append(task)
        tasks.sort(
            key=lambda task: (
                task.get("brief", {}).get("generation_index", 0),
                task.get("task_id", ""),
            )
        )
        return tasks

    def list_publication_tasks(self, brand_id: int, *, limit: int = 100) -> list[dict]:
        """Return preparation and delivery tasks for one brand, newest first."""
        tasks = []
        for key in self.r.scan_iter(match=f"{TASK_PREFIX}*", count=200):
            raw = self.r.get(key)
            if not raw:
                continue
            try:
                task = json.loads(raw)
            except json.JSONDecodeError:
                continue
            brief = task.get("brief") or {}
            if (
                brief.get("workflow") in {
                    "prepare_publication", "deliver_publication", "publish_idea",
                }
                and brief.get("brand_id") == brand_id
            ):
                tasks.append(task)
        tasks.sort(key=lambda task: task.get("created_at") or 0, reverse=True)
        return tasks[:limit]

    # ── Espera de finalización (pub/sub + polling de seguridad) ─
    def publish_update(self, task_id: str, status: str) -> None:
        try:
            self.r.publish(f"{CHANNEL_PREFIX}{task_id}", status)
        except Exception as exc:  # noqa: BLE001
            logger.debug("publish falló (no crítico): %s", exc)

    def wait_for_status(
        self,
        task_id: str,
        statuses: Iterable[str] = (STATUS_COMPLETED, STATUS_FAILED),
        *,
        timeout: float = 300.0,
        poll: float = 0.25,
    ) -> dict:
        """Bloquea hasta que la tarea alcance uno de ``statuses``."""
        wanted = set(statuses)
        deadline = time.time() + timeout
        pubsub = None
        try:
            pubsub = self.r.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(f"{CHANNEL_PREFIX}{task_id}")
            while time.time() < deadline:
                task = self.get(task_id)
                if task and task.get("status") in wanted:
                    return task
                msg = pubsub.get_message(timeout=poll)
                if msg and msg.get("type") == "message":
                    continue
            task = self.get(task_id)
            if task and task.get("status") in wanted:
                return task
            raise TimeoutError(
                f"tarea {task_id} no llegó a {sorted(wanted)} en {timeout}s "
                f"(estado: {task.get('status') if task else 'desconocida'})"
            )
        finally:
            if pubsub is not None:
                try:
                    pubsub.close()
                except Exception:  # noqa: BLE001
                    pass


__all__ = [
    "TaskStore",
    "TASK_PREFIX",
    "STATUS_RUNNING",
    "STATUS_COMPLETED",
    "STATUS_FAILED",
    "default_redis_url",
]
