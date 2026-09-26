"""Conexión y utilidades de base de datos."""
import os

import psycopg2
from psycopg2.extras import RealDictCursor

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "ideation_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASS = os.getenv("POSTGRES_PASSWORD", "password")


def get_db_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASS,
    )


def query_db(sql: str, params: tuple = None) -> list[dict]:
    """Ejecuta SELECT y devuelve lista de dicts."""
    conn = get_db_connection()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def execute_db(sql: str, params: tuple = None) -> int | None:
    """Ejecuta INSERT/UPDATE/DELETE y devuelve lastrowid o None."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        last_id = cur.lastrowid if cur.description is None else cur.fetchone()[0] if cur.description else None
        conn.commit()
        cur.close()
        return last_id
    finally:
        conn.close()
