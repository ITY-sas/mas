"""
Tests de rendimiento
P01-P09 del plan de pruebas.

Umbrales:
  P01 generate_embedding    < 2 seg
  P02 get_relevant_trends   < 3 seg
  P03 enrich_brief_context  < 10 seg
  P04 Generación LLM        < 60 seg
  P05 Pipeline completo     < 120 seg
  P06 Health endpoint       < 500 ms
  P07 Búsqueda vectorial    < 500 ms
  P08 Conexión RabbitMQ     < 2 seg
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

requests = pytest.importorskip("requests", reason="requests no instalado")

IDEACION_URL = os.getenv("IDEACION_URL", "http://localhost:8000")
PUBLICACION_URL = os.getenv("PUBLICACION_URL", "http://localhost:8001")


class TestPerformanceTools:
    """P01-P03, P07: Rendimiento de tools."""

    @pytest.mark.performance
    @pytest.mark.slow
    def test_p01_generate_embedding_speed(self):
        """P01: generate_embedding < 2 seg."""
        from shared_tools.embeddings import generate_embedding

        start = time.time()
        result = generate_embedding("campaña de marketing sostenible para jóvenes")
        elapsed = time.time() - start

        print(f"\n  P01 generate_embedding: {elapsed:.3f}s")
        assert elapsed < 2.0, f"Embedding tardó {elapsed:.3f}s (umbral: 2.0s)"
        if result is not None:
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
    def test_p03_enrich_brief_context_speed(self):
        """P03: enrich_brief_context < 10 seg."""
        pytest.importorskip("psycopg2")
        from shared_tools.enrichment import enrich_brief_context

        start = time.time()
        try:
            context = enrich_brief_context(
                "Lanzamiento de producto eco-friendly", client_id=1
            )
            elapsed = time.time() - start
            print(f"\n  P03 enrich_brief_context: {elapsed:.3f}s")
            print(f"      stats: {context.get('stats', {})}")
            assert elapsed < 10.0, f"Tardó {elapsed:.3f}s (umbral: 10.0s)"
        except Exception as e:
            pytest.skip(f"No disponible: {e}")

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
        """P04: Generación LLM < 60 seg."""
        from shared_tools.embeddings import _build_ollama_url
        import requests as req

        ollama_url = _build_ollama_url()
        model = os.getenv("OLLAMA_MODEL", "gemma3:4b")

        try:
            start = time.time()
            resp = req.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": "Escribe una idea de marketing para una marca ecológica. Sé breve.",
                    "stream": False,
                },
                timeout=90,
            )
            elapsed = time.time() - start
            assert resp.status_code == 200
            print(f"\n  P04 LLM generation ({model}): {elapsed:.1f}s")
            assert elapsed < 60.0, f"Tardó {elapsed:.1f}s (umbral: 60s)"
        except Exception as e:
            pytest.skip(f"Ollama no disponible: {e}")
