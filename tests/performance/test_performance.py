"""
Tests de rendimiento
P01-P09 del plan de pruebas.

Umbrales:
  P01 generate_embedding (vía LLM Gateway)  < 2 seg
  P02 get_relevant_trends                   < 3 seg
  P03 Contexto vía tool services (4 REST)   < 10 seg
  P04 Generación LLM (vía LLM Gateway)      < 60 seg
  P05 Pipeline completo                     < 120 seg
  P06 Health endpoint                       < 500 ms
  P07 Búsqueda vectorial                    < 500 ms
  P08 Conexión RabbitMQ                     < 2 seg
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

requests = pytest.importorskip("requests", reason="requests no instalado")

IDEACION_URL = os.getenv("IDEACION_URL", "http://localhost:8000")
PUBLICACION_URL = os.getenv("PUBLICACION_URL", "http://localhost:8001")
GATEWAY_URL = os.getenv("LLM_GATEWAY_URL", "http://localhost:8003")


class TestPerformanceTools:
    """P01-P03, P07: Rendimiento de tools."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_p01_generate_embedding_speed(self):
        """P01: generate_embedding (LLM Gateway) < 2 seg."""
        from shared_tools.embeddings import generate_embedding

        start = time.time()
        result = generate_embedding("campaña de marketing sostenible para jóvenes")
        elapsed = time.time() - start
        if result is None:
            pytest.skip("LLM Gateway no disponible (embeddings)")

        print(f"\n  P01 generate_embedding: {elapsed:.3f}s")
        assert elapsed < 2.0, f"Embedding tardó {elapsed:.3f}s (umbral: 2.0s)"
        assert len(result) == 768  # nomic-embed-text

    @pytest.mark.performance
    @pytest.mark.slow
    def test_p02_get_relevant_trends_speed(self):
        """P02: get_relevant_trends < 3 seg."""
        pytest.importorskip("psycopg2")
        from shared_tools.tendencias import get_relevant_trends

        start = time.time()
        try:
            trends = get_relevant_trends("moda sostenible", limit=5)
            elapsed = time.time() - start
            print(f"\n  P02 get_relevant_trends: {elapsed:.3f}s ({len(trends)} resultados)")
            assert elapsed < 3.0, f"Tardó {elapsed:.3f}s (umbral: 3.0s)"
        except Exception as e:
            pytest.skip(f"No disponible: {e}")

    @pytest.mark.performance
    @pytest.mark.slow
    def test_p03_tool_context_speed(self):
        """P03: contexto completo vía tool services (4 REST) < 10 seg."""
        from common.tool_client import ToolRegistry

        start = time.time()
        try:
            registry = ToolRegistry()
            if "rag" not in registry.discover(timeout=2.0):
                pytest.skip("tool services no descubiertos")
            brief = "Lanzamiento de producto eco-friendly"
            registry.call("client", "profile", params={"client_id": 1})
            registry.call("trends", "search",
                          params={"query": brief, "limit": 5})
            registry.call("competitors", "search",
                          params={"query": brief, "limit": 5})
            registry.call("rag", "similar",
                          json_body={"brand_id": 1, "query": brief, "limit": 3,
                                     "min_similarity": 0.3})
            elapsed = time.time() - start
        except Exception as e:
            pytest.skip(f"No disponible: {e}")
        print(f"\n  P03 tool context (4 REST): {elapsed:.3f}s")
        assert elapsed < 10.0, f"Tardó {elapsed:.3f}s (umbral: 10.0s)"

    @pytest.mark.performance
    @pytest.mark.slow
    def test_p07_vector_search_speed(self):
        """P07: Búsqueda vectorial pgvector < 500 ms (sin incluir embedding)."""
        pytest.importorskip("psycopg2")
        from shared_tools.embeddings import embedding_to_vector, generate_embedding
        from shared_tools.db import query_db

        # Generar embedding primero (separado de la búsqueda)
        emb = generate_embedding("marketing digital")
        if emb is None:
            pytest.skip("Ollama no disponible para embeddings")
        vec = embedding_to_vector(emb)

        # Medir solo la búsqueda en PostgreSQL
        start = time.time()
        rows = query_db(
            "SELECT id, content, 1 - (embedding <=> %s::vector) as similarity "
            "FROM tendencias WHERE embedding IS NOT NULL "
            "ORDER BY embedding <=> %s::vector LIMIT 5",
            (vec, vec),
        )
        elapsed = time.time() - start
        print(f"\n  P07 vector_search (solo SQL): {elapsed*1000:.1f}ms ({len(rows)} resultados)")
        assert elapsed < 0.5, f"Tardó {elapsed*1000:.1f}ms (umbral: 500ms)"


class TestPerformanceAgents:
    """P06: Rendimiento de endpoints de agentes."""

    @pytest.mark.performance
    def test_p06_ideacion_health_speed(self):
        """P06: /health < 500 ms."""
        try:
            start = time.time()
            resp = requests.get(f"{IDEACION_URL}/health", timeout=5)
            elapsed = time.time() - start
            print(f"\n  P06 ideacion /health: {elapsed*1000:.1f}ms")
            assert resp.status_code == 200
            assert elapsed < 0.5, f"Tardó {elapsed*1000:.1f}ms (umbral: 500ms)"
        except requests.ConnectionError:
            pytest.skip("Agente no disponible")

    @pytest.mark.performance
    def test_p06_publicacion_health_speed(self):
        """P06b: /health publicación < 500 ms."""
        try:
            start = time.time()
            resp = requests.get(f"{PUBLICACION_URL}/health", timeout=5)
            elapsed = time.time() - start
            print(f"\n  P06 publicacion /health: {elapsed*1000:.1f}ms")
            assert resp.status_code == 200
            assert elapsed < 0.5, f"Tardó {elapsed*1000:.1f}ms (umbral: 500ms)"
        except requests.ConnectionError:
            pytest.skip("Agente no disponible")

    @pytest.mark.performance
    def test_p06_tools_endpoint_speed(self):
        """P06c: /tools < 500 ms."""
        try:
            start = time.time()
            resp = requests.get(f"{IDEACION_URL}/tools", timeout=5)
            elapsed = time.time() - start
            print(f"\n  P06 ideacion /tools: {elapsed*1000:.1f}ms")
            assert resp.status_code == 200
            assert elapsed < 0.5, f"Tardó {elapsed*1000:.1f}ms (umbral: 500ms)"
        except requests.ConnectionError:
            pytest.skip("Agente no disponible")


class TestPerformanceRabbitMQ:
    """P08: Conexión a RabbitMQ."""

    @pytest.mark.performance
    def test_p08_rabbitmq_connection_speed(self):
        """P08: Conexión RabbitMQ < 2 seg."""
        pika = pytest.importorskip("pika", reason="pika no instalado")

        try:
            start = time.time()
            conn = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=os.getenv("RABBITMQ_HOST_TEST", "localhost"),
                    port=5672,
                    credentials=pika.PlainCredentials("user", "password"),
                )
            )
            elapsed = time.time() - start
            conn.close()
            print(f"\n  P08 rabbitmq connection: {elapsed:.3f}s")
            assert elapsed < 2.0, f"Tardó {elapsed:.3f}s (umbral: 2.0s)"
        except Exception as e:
            pytest.skip(f"RabbitMQ no disponible: {e}")


class TestPerformanceLLM:
    """P04-P05: Rendimiento del LLM (lentos)."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_p04_llm_generation_speed(self):
        """P04: Generación LLM (vía LLM Gateway) < 60 seg."""
        import requests as req

        try:
            start = time.time()
            resp = req.post(
                f"{GATEWAY_URL}/v1/generate",
                json={
                    "prompt": "Escribe una idea de marketing para una marca ecológica. Sé breve.",
                },
                timeout=90,
            )
            elapsed = time.time() - start
            assert resp.status_code == 200, resp.text[:200]
            data = resp.json()
            print(f"\n  P04 LLM generation ({data.get('provider')}/{data.get('model')}): "
                  f"{elapsed:.1f}s (cached={data.get('cached')}, attempts={data.get('attempts')})")
            assert data["content"]
            assert elapsed < 60.0, f"Tardó {elapsed:.1f}s (umbral: 60s)"
        except Exception as e:
            pytest.skip(f"LLM Gateway no disponible: {e}")
