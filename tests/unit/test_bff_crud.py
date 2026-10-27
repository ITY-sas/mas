"""
Pruebas unitarias para los endpoints CRUD y manejo de HTTP 409 Conflict en el BFF (frontend/server.py).
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from frontend.server import app

client = TestClient(app)


def test_bff_update_brand_proxy(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"status": "ok", "data": {"id": 1, "name": "EcoBrand Updated"}}

    monkeypatch.setattr("requests.put", lambda url, json, timeout: fake_resp)

    res = client.put("/api/brands/1", json={"name": "EcoBrand Updated"})
    assert res.status_code == 200
    assert res.json() == {"id": 1, "name": "EcoBrand Updated"}


def test_bff_delete_brand_proxy(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"status": "ok", "data": {"id": 1, "status": "archived"}}

    monkeypatch.setattr("requests.delete", lambda url, timeout: fake_resp)

    res = client.delete("/api/brands/1")
    assert res.status_code == 200
    assert res.json() == {"id": 1, "status": "archived"}


def test_bff_update_idea_returns_409_on_conflict(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.status_code = 409
    fake_resp.headers = {"content-type": "application/json"}
    fake_resp.json.return_value = {
        "status": "error",
        "error": "No se puede modificar la idea 5: está archivada",
    }

    monkeypatch.setattr("requests.put", lambda url, params, json, timeout: fake_resp)

    res = client.put("/api/ideas/5", params={"brand_id": 1}, json={"title": "New Title"})
    assert res.status_code == 409
    assert "No se puede modificar la idea 5" in res.json()["detail"]


def test_bff_delete_idea_returns_409_when_published(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.status_code = 409
    fake_resp.headers = {"content-type": "application/json"}
    fake_resp.json.return_value = {
        "status": "error",
        "error": "No se puede eliminar la idea 5: tiene publicaciones enviadas",
    }

    monkeypatch.setattr("requests.delete", lambda url, params, timeout: fake_resp)

    res = client.delete("/api/ideas/5", params={"brand_id": 1})
    assert res.status_code == 409
    assert "tiene publicaciones enviadas" in res.json()["detail"]


def test_bff_update_publication_returns_409_when_sent(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.status_code = 409
    fake_resp.headers = {"content-type": "application/json"}
    fake_resp.json.return_value = {
        "status": "error",
        "error": "No se puede modificar la publicación 10: ya fue enviada a Postiz",
    }

    monkeypatch.setattr("requests.put", lambda url, params, json, timeout: fake_resp)

    res = client.put("/api/publications/saved/10", params={"brand_id": 1}, json={"content": "New copy"})
    assert res.status_code == 409
    assert "ya fue enviada a Postiz" in res.json()["detail"]


def test_bff_delete_publication_returns_409_when_sent(monkeypatch):
    fake_resp = MagicMock()
    fake_resp.status_code = 409
    fake_resp.headers = {"content-type": "application/json"}
    fake_resp.json.return_value = {
        "status": "error",
        "error": "No se puede eliminar la publicación 10: ya fue enviada a Postiz",
    }

    monkeypatch.setattr("requests.delete", lambda url, params, timeout: fake_resp)

    res = client.delete("/api/publications/saved/10", params={"brand_id": 1})
    assert res.status_code == 409
    assert "ya fue enviada a Postiz" in res.json()["detail"]
