"""
Historial de chat del orquestador — **PostgreSQL** (persistencia durable).

Requisito de arquitectura #1: el orquestador es stateless y delega la
memoria en la capa de persistencia:

- ciclo de planificación → Redis (checkpoints LangGraph + TaskStore)
- **historial de chat** → esta tabla PostgreSQL

Una fila por turno (``user`` = brief recibido, ``assistant`` = idea +
publicación generadas).
"""
from __future__ import annotations

import logging
import os

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("orchestrator.history")

DDL = """
CREATE TABLE IF NOT EXISTS chat_history (
    id          SERIAL PRIMARY KEY,
    task_id     TEXT NOT NULL,
    client_id   INTEGER,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool')),
    content     TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_chat_history_task ON chat_history (task_id, id);
"""


def _connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "ideation_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "password"),
    )


def init_history_table() -> None:
    """Crea la tabla si no existe (idempotente, llamado al arrancar)."""
    conn = _connection()
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
        logger.info("tabla chat_history preparada ✓")
    finally:
        conn.close()


def add_message(task_id: str, client_id, role: str, content: str) -> None:
    """Inserta un turno del historial de chat."""
    conn = _connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_history (task_id, client_id, role, content) "
                "VALUES (%s, %s, %s, %s)",
                (task_id, client_id, role, content),
            )
        conn.commit()
    finally:
        conn.close()


def get_history(task_id: str) -> list[dict]:
    """Devuelve los turnos de una tarea ordenados cronológicamente."""
    conn = _connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, task_id, client_id, role, content, created_at "
                "FROM chat_history WHERE task_id = %s ORDER BY id",
                (task_id,),
            )
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
