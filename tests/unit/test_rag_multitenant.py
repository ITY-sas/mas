import pytest

from shared_tools import rag

pytestmark = pytest.mark.unit


def test_idea_search_scopes_sql_to_brand(monkeypatch):
    captured = {}

    monkeypatch.setattr(rag, "generate_embedding", lambda text: [0.1, 0.2])

    def fake_query(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return [{"id": 1, "client_id": 10, "content": "idea A", "similarity": 0.9}]

    monkeypatch.setattr(rag, "query_db", fake_query)

    result = rag.search_similar_ideas(7, "campaña de prueba", limit=3, min_similarity=0.3)

    assert result[0]["content"] == "idea A"
    assert "brand_id = %s" in captured["sql"]
    assert captured["params"][1] == 7


def test_private_generic_search_requires_brand(monkeypatch):
    with pytest.raises(ValueError, match="brand_id es obligatorio"):
        rag.search_similar_content("ideas_generadas", None, "consulta")


def test_idea_library_queries_are_scoped_to_brand(monkeypatch):
    from shared_tools import db
    from tool_services.tool_rag import main as rag_tool

    calls = []

    def fake_query(sql, params):
        calls.append((sql, params))
        if "count(*)" in sql:
            return [{"total": 1}]
        return [{
            "id": 12,
            "brand_id": 7,
            "client_id": 70,
            "generation_batch_id": None,
            "generation_index": None,
            "content": '{"title":"Idea privada"}',
            "created_at": None,
        }]

    monkeypatch.setattr(db, "query_db", fake_query)
    result = rag_tool.op_list_ideas(7, limit=10, offset=0)

    assert result["total"] == 1
    assert all("brand_id = %s" in sql for sql, _ in calls)
    assert all(params[0] == 7 for _, params in calls)


def test_get_idea_does_not_return_another_brands_row(monkeypatch):
    from shared_tools import db
    from tool_services.tool_rag import main as rag_tool

    captured = {}

    def fake_query(sql, params):
        captured.update(sql=sql, params=params)
        return []

    monkeypatch.setattr(db, "query_db", fake_query)
    assert rag_tool.op_get_idea(brand_id=7, idea_id=99) is None
    assert "brand_id = %s AND id = %s" in captured["sql"]
    assert captured["params"] == (7, 99)


def test_batch_status_is_scoped_to_brand(monkeypatch):
    from shared_tools import db
    from tool_services.tool_rag import main as rag_tool

    captured = {}

    def fake_query(sql, params):
        captured.update(sql=sql, params=params)
        return []

    monkeypatch.setattr(db, "query_db", fake_query)
    result = rag_tool.op_ideas_batch_status(7, "batch-123")
    assert result["brand_id"] == 7
    assert "brand_id = %s AND generation_batch_id = %s" in captured["sql"]
    assert captured["params"] == (7, "batch-123")


def test_batch_idea_save_is_idempotent_per_brand(monkeypatch):
    from shared_tools import db, embeddings
    from tool_services.tool_rag import main as rag_tool

    captured = {}

    def fake_execute(sql, params):
        captured.update(sql=sql, params=params)
        return 44

    monkeypatch.setattr(db, "execute_db", fake_execute)
    monkeypatch.setattr(embeddings, "generate_embedding", lambda content: None)
    monkeypatch.setattr(embeddings, "embedding_to_vector", lambda embedding: None)

    assert rag_tool.op_save_idea(7, 70, "{}", "batch-123", 0) == {"id": 44}
    assert "ON CONFLICT (brand_id, generation_batch_id, generation_index)" in captured["sql"]
    assert captured["params"][:4] == (70, 7, "batch-123", 0)
