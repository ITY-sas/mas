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
