"""
Tests unitarios para ciclo de vida, estados y operaciones CRUD (Fase 3 del Plan).
Verifica:
- Exclusión de registros archivados en búsquedas RAG.
- Recálculo de embeddings al editar ideas y publicaciones.
- Inmutabilidad y bloqueo 409 ante publicaciones ya enviadas a redes.
- Soft-delete e integridad referencial.
- CRUD y configuración RAG en marcas.
"""
import os
import sys
import json
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from shared_tools import db, embeddings, rag
from shared_tools.rag import LifecycleConflictError
from tool_services.tool_rag import main as tool_rag_service
from tool_services.tool_client import main as tool_client_service

pytestmark = pytest.mark.unit


# ── 1. RAG & Exclusión de Archivados ───────────────────────────
def test_search_similar_ideas_excludes_archived(monkeypatch):
    """T-CRUD-01: search_similar_ideas debe ignorar ideas con status='archived'."""
    captured = {}

    def fake_query(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return [
            {"id": 1, "client_id": 1, "content": "Idea activa", "similarity": 0.85}
        ]

    monkeypatch.setattr(rag, "query_db", fake_query)
    monkeypatch.setattr(rag, "generate_embedding", lambda text: [0.1, 0.2, 0.3])
    monkeypatch.setattr(rag, "embedding_to_vector", lambda vec: "[0.1,0.2,0.3]")

    results = rag.search_similar_ideas(brand_id=42, query_text="ropa ecológica", limit=3)

    assert len(results) == 1
    assert "!= 'archived'" in captured["sql"]
    assert captured["params"][1] == 42


# ── 2. Edición y Recálculo de Embeddings ────────────────────────
def test_update_idea_regenerates_embedding(monkeypatch):
    """T-CRUD-02: Editar idea debe recalcular su embedding y marcar updated_at."""
    executed = []
    generated = []

    def fake_query(sql, params):
        return [{"id": 10, "brand_id": 5, "status": "approved"}]

    def fake_execute(sql, params):
        executed.append({"sql": sql, "params": params})
        return 1

    def fake_embed(text):
        generated.append(text)
        return [0.4, 0.5]

    monkeypatch.setattr(rag, "query_db", fake_query)
    monkeypatch.setattr(rag, "execute_db", fake_execute)
    monkeypatch.setattr(rag, "generate_embedding", fake_embed)
    monkeypatch.setattr(rag, "embedding_to_vector", lambda v: "[0.4,0.5]")

    res = rag.update_idea(idea_id=10, brand_id=5, content="Nuevo guion actualizado")

    assert res["id"] == 10
    assert res["content"] == "Nuevo guion actualizado"
    assert "Nuevo guion actualizado" in generated
    assert len(executed) == 1
    assert "updated_at = NOW()" in executed[0]["sql"]
    assert executed[0]["params"][0] == "Nuevo guion actualizado"
    assert executed[0]["params"][1] == "[0.4,0.5]"


def test_update_archived_idea_raises_conflict(monkeypatch):
    """No se permite editar una idea que ya fue archivada."""
    monkeypatch.setattr(rag, "query_db", lambda sql, params: [{"id": 10, "brand_id": 5, "status": "archived"}])

    with pytest.raises(LifecycleConflictError, match="No se puede editar una idea archivada"):
        rag.update_idea(idea_id=10, brand_id=5, content="Intento de edición")


# ── 3. Eliminación e Integridad de Máquina de Estados ───────────
def test_delete_idea_with_published_post_raises_conflict(monkeypatch):
    """T-CRUD-03: No se puede eliminar una idea con publicaciones despachadas a redes."""
    def fake_query(sql, params):
        if "FROM ideas_generadas" in sql:
            return [{"id": 10, "brand_id": 5, "status": "published"}]
        if "FROM publicaciones_generadas" in sql:
            return [{"id": 99, "status": "sent_to_postiz"}]
        return []

    monkeypatch.setattr(rag, "query_db", fake_query)

    with pytest.raises(LifecycleConflictError, match="ya tiene publicaciones despachadas"):
        rag.delete_idea(idea_id=10, brand_id=5)


def test_delete_idea_soft_deletes_and_cascades_drafts(monkeypatch):
    """Idea sin posts enviados se archiva y archiva borradores pendientes."""
    executed = []

    def fake_query(sql, params):
        if "FROM ideas_generadas" in sql:
            return [{"id": 10, "brand_id": 5, "status": "approved"}]
        if "FROM publicaciones_generadas" in sql:
            return []
        return []

    def fake_execute(sql, params):
        executed.append({"sql": sql, "params": params})
        return 1

    monkeypatch.setattr(rag, "query_db", fake_query)
    monkeypatch.setattr(rag, "execute_db", fake_execute)

    res = rag.delete_idea(idea_id=10, brand_id=5)

    assert res == {"id": 10, "brand_id": 5, "status": "archived"}
    assert len(executed) == 2
    assert "UPDATE ideas_generadas SET status = 'archived'" in executed[0]["sql"]
    assert "UPDATE publicaciones_generadas SET status = 'archived'" in executed[1]["sql"]


# ── 4. Inmutabilidad de Publicaciones en Redes ──────────────────
def test_update_sent_publication_raises_conflict(monkeypatch):
    """T-CRUD-04: Una publicación enviada a Postiz es inmutable."""
    monkeypatch.setattr(rag, "get_publicacion", lambda pub_id, brand_id: {
        "id": pub_id, "brand_id": brand_id, "status": "sent_to_postiz", "content": "Copy original"
    })

    with pytest.raises(LifecycleConflictError, match="Publicación inmutable"):
        rag.update_publicacion(pub_id=7, brand_id=2, content="Nuevo copy no permitido")


def test_delete_sent_publication_raises_conflict(monkeypatch):
    """Una publicación enviada a redes no se puede eliminar."""
    monkeypatch.setattr(rag, "get_publicacion", lambda pub_id, brand_id: {
        "id": pub_id, "brand_id": brand_id, "status": "sent_to_postiz", "content": "Copy original"
    })

    with pytest.raises(LifecycleConflictError, match="la publicación ya fue enviada"):
        rag.delete_publicacion(pub_id=7, brand_id=2)


def test_update_draft_publication_recalculates_embedding(monkeypatch):
    """Actualizar borrador de publicación recalcula su vector."""
    executed = []

    monkeypatch.setattr(rag, "get_publicacion", lambda pub_id, brand_id: {
        "id": pub_id, "brand_id": brand_id, "status": "draft", "content": "Borrador viejo"
    })
    monkeypatch.setattr(rag, "generate_embedding", lambda text: [0.9, 0.8])
    monkeypatch.setattr(rag, "embedding_to_vector", lambda v: "[0.9,0.8]")

    def fake_execute(sql, params):
        executed.append({"sql": sql, "params": params})
        return 1

    monkeypatch.setattr(rag, "execute_db", fake_execute)

    res = rag.update_publicacion(pub_id=7, brand_id=2, content="Borrador pulido")

    assert res["id"] == 7
    assert res["content"] == "Borrador pulido"
    assert len(executed) == 1
    assert "embedding = %s::vector" in executed[0]["sql"]
    assert executed[0]["params"][0] == "Borrador pulido"
    assert executed[0]["params"][1] == "[0.9,0.8]"


# ── 5. CRUD de Marcas y Configuración RAG ───────────────────────
def test_brand_crud_lifecycle(monkeypatch):
    """T-CRUD-05: Actualizar perfil de marca y rag_config, y soft delete."""
    executed = []

    brand_data = {
        "id": 3,
        "organization_id": 1,
        "name": "EcoBrand",
        "slug": "ecobrand",
        "status": "active",
        "profile_marca": "Productos sostenibles",
        "rag_config": {"enabled": True, "min_similarity": 0.4},
    }

    monkeypatch.setattr(db, "query_db", lambda sql, params: [brand_data])

    def fake_execute(sql, params):
        executed.append({"sql": sql, "params": params})
        return 1

    monkeypatch.setattr(db, "execute_db", fake_execute)

    # 1. Get
    got = tool_client_service.op_get_brand(3)
    assert got["id"] == 3
    assert got["rag_config"] == {"enabled": True, "min_similarity": 0.4}

    # 2. Update
    update_body = tool_client_service.BrandUpdateBody(
        name="EcoBrand Pro",
        rag_config={"enabled": True, "min_similarity": 0.5},
    )
    res_update = tool_client_service.op_update_brand(3, update_body)
    assert len(executed) == 2
    assert "UPDATE brands SET" in executed[0]["sql"]
    assert "name = %s" in executed[0]["sql"]
    assert "rag_config = %s::jsonb" in executed[0]["sql"]
    assert "UPDATE clientes SET" in executed[1]["sql"]

    # 3. Soft Delete
    res_delete = tool_client_service.op_delete_brand(3)
    assert res_delete == {"id": 3, "status": "archived"}
    assert "UPDATE brands SET status = 'archived'" in executed[2]["sql"]


# ── 6. Endpoints FastAPI: Verificación de Código 409 ───────────
def test_tool_rag_fastapi_endpoints_return_409(monkeypatch):
    """Los endpoints PUT y DELETE retornan HTTP 409 cuando se violan reglas de ciclo de vida."""
    from fastapi.testclient import TestClient

    def fake_update_idea(*args, **kwargs):
        raise LifecycleConflictError("Conflicto de prueba en idea")

    def fake_delete_idea(*args, **kwargs):
        raise LifecycleConflictError("Conflicto de prueba al borrar idea")

    def fake_update_pub(*args, **kwargs):
        raise LifecycleConflictError("Conflicto de prueba en publicación")

    def fake_delete_pub(*args, **kwargs):
        raise LifecycleConflictError("Conflicto de prueba al borrar publicación")

    monkeypatch.setattr(tool_rag_service, "op_update_idea", fake_update_idea)
    monkeypatch.setattr(tool_rag_service, "op_delete_idea", fake_delete_idea)
    monkeypatch.setattr(tool_rag_service, "op_update_publicacion", fake_update_pub)
    monkeypatch.setattr(tool_rag_service, "op_delete_publicacion", fake_delete_pub)

    client = TestClient(tool_rag_service.app)

    # PUT idea conflict
    resp1 = client.put("/ideas/1", json={"brand_id": 1, "content": "text"})
    assert resp1.status_code == 409
    assert "Conflicto de prueba en idea" in resp1.json()["error"]

    # DELETE idea conflict
    resp2 = client.delete("/ideas/1?brand_id=1")
    assert resp2.status_code == 409
    assert "Conflicto de prueba al borrar idea" in resp2.json()["error"]

    # PUT pub conflict
    resp3 = client.put("/publicaciones/1", json={"brand_id": 1, "content": "text"})
    assert resp3.status_code == 409
    assert "Conflicto de prueba en publicación" in resp3.json()["error"]

    # DELETE pub conflict
    resp4 = client.delete("/publicaciones/1?brand_id=1")
    assert resp4.status_code == 409
    assert "Conflicto de prueba al borrar publicación" in resp4.json()["error"]
