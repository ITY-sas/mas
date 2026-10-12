"""Unit tests for platform-specific publication persistence and Postiz payloads."""
import os
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# tool-postiz starts its optional AMQP RPC consumer at import time.
_previous_amqp_enabled = os.environ.get("AMQP_ENABLED")
os.environ["AMQP_ENABLED"] = "false"
from tool_services.tool_postiz import main as postiz_service  # noqa: E402
if _previous_amqp_enabled is None:
    os.environ.pop("AMQP_ENABLED", None)
else:
    os.environ["AMQP_ENABLED"] = _previous_amqp_enabled

pytestmark = pytest.mark.unit


def test_postiz_channels_are_scoped_to_brand_and_selected_integrations(monkeypatch):
    from shared_tools import db

    captured = {}
    rows = [
        {"external_id": "ig-1", "provider": "instagram", "display_name": "Brand IG", "settings": {"__type": "instagram"}},
        {"external_id": "li-1", "provider": "linkedin", "display_name": "Brand LI", "settings": {}},
    ]

    def fake_query(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return rows

    monkeypatch.setattr(db, "query_db", fake_query)

    result = postiz_service.op_channels(brand_id=8, integration_ids=["li-1"])

    assert "brand_id = %s" in captured["sql"]
    assert captured["params"] == (8,)
    assert result == {"brand_id": 8, "channels": [{
        "external_id": "li-1", "provider": "linkedin", "display_name": "Brand LI", "configured": False,
    }]}


def test_available_postiz_integrations_are_sanitized(monkeypatch):
    monkeypatch.setattr(postiz_service, "op_integrations", lambda: {
        "integrations": [{
            "id": "ig-1", "identifier": "instagram", "name": "Brand IG",
            "accessToken": "must-not-leak",
        }]
    })

    result = postiz_service.op_available_integrations()

    assert result == [{
        "external_id": "ig-1", "provider": "instagram", "display_name": "Brand IG",
    }]
    assert "accessToken" not in result[0]


def test_link_postiz_integration_persists_brand_provider_and_type(monkeypatch):
    from shared_tools import db

    monkeypatch.setattr(postiz_service, "op_available_integrations", lambda: [{
        "external_id": "li-1", "provider": "linkedin", "display_name": "Brand LinkedIn",
    }])
    monkeypatch.setattr(db, "query_db", lambda sql, params: [])
    captured = {}

    def fake_execute(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return 51

    monkeypatch.setattr(db, "execute_db", fake_execute)
    result = postiz_service.op_link_channel(
        postiz_service.LinkChannelBody(brand_id=8, external_id="li-1")
    )

    assert result["id"] == 51
    assert result["configured"] is True
    assert "ON CONFLICT (provider, external_id)" in captured["sql"]
    assert json.loads(captured["params"][4]) == {"__type": "linkedin"}


def test_postiz_create_post_uses_content_for_each_integration(monkeypatch):
    from shared_tools import db

    rows = [
        {"external_id": "ig-1", "provider": "instagram", "settings": {"__type": "instagram"}},
        {"external_id": "li-1", "provider": "linkedin", "settings": {"__type": "linkedin"}},
    ]
    monkeypatch.setattr(db, "query_db", lambda sql, params: rows)
    captured = {}

    def fake_request(method, path, **kwargs):
        captured.update(method=method, path=path, **kwargs)
        return {"ok": True}

    monkeypatch.setattr(postiz_service, "_request", fake_request)
    body = postiz_service.CreatePostBody(
        brand_id=8,
        content="legacy fallback",
        integration_ids=["ig-1", "li-1"],
        contents={"ig-1": "Instagram caption", "li-1": "LinkedIn post"},
        mode="schedule",
        publish_at="2026-11-05T17:30:00Z",
    )

    postiz_service.op_create_post(body)

    posts = captured["json"]["posts"]
    assert captured["method"] == "POST"
    assert captured["path"] == "/posts"
    assert captured["json"]["type"] == "schedule"
    assert captured["json"]["date"] == "2026-11-05T17:30:00Z"
    assert posts[0]["value"][0]["content"] == "Instagram caption"
    assert posts[1]["value"][0]["content"] == "LinkedIn post"


def test_postiz_draft_includes_required_iso_date(monkeypatch):
    from datetime import datetime
    from shared_tools import db

    monkeypatch.setattr(db, "query_db", lambda sql, params: [
        {"external_id": "li-1", "provider": "linkedin", "settings": {"__type": "linkedin"}},
    ])
    captured = {}

    def fake_request(method, path, **kwargs):
        captured.update(method=method, path=path, **kwargs)
        return {"ok": True}

    monkeypatch.setattr(postiz_service, "_request", fake_request)
    postiz_service.op_create_post(postiz_service.CreatePostBody(
        brand_id=8,
        content="LinkedIn draft",
        integration_ids=["li-1"],
        mode="draft",
    ))

    date = captured["json"]["date"]
    assert isinstance(date, str) and date.endswith("Z")
    assert datetime.fromisoformat(date.replace("Z", "+00:00")).tzinfo is not None


def test_rag_persists_platform_with_publication(monkeypatch):
    from shared_tools import db, embeddings
    from tool_services.tool_rag.main import op_save_publicacion

    captured = {}

    def fake_execute(sql, params):
        captured["sql"] = sql
        captured["params"] = params
        return 19

    monkeypatch.setattr(db, "execute_db", fake_execute)
    monkeypatch.setattr(embeddings, "generate_embedding", lambda text: [0.1, 0.2])
    monkeypatch.setattr(embeddings, "embedding_to_vector", lambda vector: "[0.1,0.2]")

    result = op_save_publicacion(
        brand_id=8,
        client_id=3,
        content="LinkedIn variant",
        idea_id=5,
        platform="linkedin",
    )

    assert "platform" in captured["sql"]
    assert captured["params"] == (3, 8, 5, "linkedin", "LinkedIn variant", "[0.1,0.2]")
    assert result == {"id": 19}
