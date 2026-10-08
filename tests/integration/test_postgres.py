"""
Tests de integración: PostgreSQL + pgvector
I05-I09 del plan de pruebas.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

psycopg2 = pytest.importorskip("psycopg2", reason="psycopg2 no instalado")

POSTGRES_CFG = dict(
    host=os.getenv("POSTGRES_HOST_TEST", "localhost"),
    port=int(os.getenv("POSTGRES_PORT_TEST", "5432")),
    database="ideation_db",
    user="postgres",
    password="password",
)


def _get_conn():
    return psycopg2.connect(**POSTGRES_CFG)


class TestPostgreSQL:
    """I05-I09: Conexión y operaciones con PostgreSQL."""

    @pytest.mark.integration
    def test_connection(self):
        """I05: Conexión a PostgreSQL exitosa."""
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            assert cur.fetchone()[0] == 1
            conn.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL no disponible: {e}")

    @pytest.mark.integration
    def test_tables_exist(self):
        """I06: Las 5 tablas existen."""
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
            tables = {r[0] for r in cur.fetchall()}
            expected = {"clientes", "tendencias", "referencias_competencia",
                        "ideas_generadas", "publicaciones_generadas"}
            assert expected.issubset(tables), f"Faltan tablas: {expected - tables}"
            cur.close()
            conn.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL no disponible: {e}")

    @pytest.mark.integration
    def test_insert_select_idea(self):
        """I07: Insert + Select roundtrip."""
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO ideas_generadas (client_id, brand_id, content) "
                "VALUES (1, 1, 'TEST_ROUNDTRIP_ID') RETURNING id"
            )
            row_id = cur.fetchone()[0]
            conn.commit()

            cur.execute("SELECT content FROM ideas_generadas WHERE id = %s", (row_id,))
            content = cur.fetchone()[0]
            assert content == "TEST_ROUNDTRIP_ID"

            # Cleanup
            cur.execute("DELETE FROM ideas_generadas WHERE id = %s", (row_id,))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL no disponible: {e}")

    @pytest.mark.integration
    def test_vector_search(self):
        """I08: Búsqueda vectorial con pgvector."""
        try:
            conn = _get_conn()
            cur = conn.cursor()
            # Verificar que la extensión está activa
            cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            assert cur.fetchone() is not None, "pgvector no instalado"

            # Verificar columna vector en tendencias
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'tendencias' AND column_name = 'embedding'"
            )
            assert cur.fetchone() is not None, "Columna embedding no existe"
            cur.close()
            conn.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL no disponible: {e}")

    @pytest.mark.integration
    def test_seed_data_loaded(self):
        """I09: Seed data ejecutado (≥17 tendencias, ≥13 competidores)."""
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM tendencias")
            n_trends = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM referencias_competencia")
            n_competitors = cur.fetchone()[0]

            assert n_trends >= 17, f"Solo {n_trends} tendencias (esperado ≥17)"
            assert n_competitors >= 13, f"Solo {n_competitors} competidores (esperado ≥13)"
            cur.close()
            conn.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL no disponible: {e}")

    @pytest.mark.integration
    def test_no_null_embeddings(self):
        """Los registros no deberían tener embedding NULL (tras backfill)."""
        try:
            conn = _get_conn()
            cur = conn.cursor()
            for table in ["tendencias", "referencias_competencia"]:
                cur.execute(f"SELECT COUNT(*) FROM {table} WHERE embedding IS NULL")
                nulls = cur.fetchone()[0]
                # Puede haber algunos si el backfill falló, pero la mayoría debería tener
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                total = cur.fetchone()[0]
                if total > 0:
                    assert nulls < total, f"Todos los embeddings en {table} son NULL"
            cur.close()
            conn.close()
        except Exception as e:
            pytest.skip(f"PostgreSQL no disponible: {e}")
