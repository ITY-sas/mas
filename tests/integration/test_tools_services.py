"""
Tests de integración de los 6 microservicios de tools (Tools-as-a-Service).

Verifican por cada servicio:
- ``GET /health``
- ``GET /.well-known/tool-manifest`` (contrato de Tool Discovery)
- su operación principal vía REST (envelope uniforme)
- invocación RPC por eventos ``tool.*.rpc`` (al menos en un servicio)

Se saltan si ``docker compose up -d --build`` no está levantado.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pytest

pytestmark = pytest.mark.integration

requests = pytest.importorskip("requests", reason="requests no instalado")

from common.contracts import TOOL_MANIFEST_PATH, validate_manifest  # noqa: E402

# service → (puerto, operación principal)
TOOLS = {
    "client": (8010, ("GET", "/profile", {"client_id": 1})),
    "trends": (8011, ("GET", "/search", {"query": "moda sostenible", "limit": 3})),
    "competitors": (8012, ("GET", "/search", {"query": "moda sostenible", "limit": 3})),
    "rag": (8013, ("POST", "/similar",
                   {"query": "moda sostenible", "limit": 3, "min_similarity": 0.3})),
    "news": (8014, ("GET", "/news", {"query": "marketing", "limit": 2})),
    "trending": (8015, ("GET", "/trending", {"query": "marketing"})),
}


def _get(port: int, path: str, params: dict | None = None, timeout: float = 8.0):
    try:
        return requests.get(f"http://localhost:{port}{path}",
                            params=params, timeout=timeout)
    except requests.ConnectionError:
        pytest.skip(f"tool en localhost:{port} no disponible")


def _post(port: int, path: str, body: dict, timeout: float = 20.0):
    try:
        return requests.post(f"http://localhost:{port}{path}",
                             json=body, timeout=timeout)
    except requests.ConnectionError:
        pytest.skip(f"tool en localhost:{port} no disponible")


@pytest.mark.parametrize("tool", sorted(TOOLS))
def test_tool_health(tool):
    """Cada tool service responde healthy con su identidad."""
    port = TOOLS[tool][0]
    resp = _get(port, "/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["tool"] == tool
    assert data["service"] == f"tool-{tool}"


@pytest.mark.parametrize("tool", sorted(TOOLS))
def test_tool_manifest_contract(tool):
    """Manifiesto descubrible con forma de contrato válida."""
    port = TOOLS[tool][0]
    resp = _get(port, TOOL_MANIFEST_PATH)

    assert resp.status_code == 200
    manifest = resp.json()
    validate_manifest(manifest)
    assert manifest["name"] == tool
    assert "amqp" in manifest["transport"]
    assert manifest["amqp_queue"] == f"tool.{tool}.rpc"
    assert any(op["path"].startswith("/") for op in manifest["operations"])


@pytest.mark.parametrize("tool", sorted(TOOLS))
def test_tool_main_operation_envelope(tool):
    """La operación principal devuelve el envelope uniforme status=ok."""
    port = TOOLS[tool][0]
    _method, path, body = TOOLS[tool][1]
    resp = _post(port, path, body) if _method == "POST" else _get(port, path, body)

    assert resp.status_code == 200, resp.text[:300]
    envelope = resp.json()
    assert envelope["status"] == "ok", envelope.get("error")
    assert envelope["tool"].startswith(tool)
    assert "duration_ms" in envelope
    assert "data" in envelope


def test_rag_stats_own_tables():
    """tool-rag es dueño de ideas_generadas / publicaciones_generadas."""
    resp = _get(8013, "/stats")

    data = resp.json()["data"]
    assert data["ideas"] >= 1
    assert data["publicaciones"] >= 1


def test_rpc_amqp_invocation():
    """Un tool service atiende RPC por eventos (tool.task.triggered)."""
    sys.path.insert(0, str(ROOT))
    from common.events import TOOL_TASK_TRIGGERED, Event, rpc_call, tool_rpc_queue

    try:
        reply = rpc_call(
            tool_rpc_queue("trends"),
            Event(event_type=TOOL_TASK_TRIGGERED, task_id="it-rpc",
                  tool="trends", operation="search",
                  payload={"query": "moda sostenible", "limit": 2}),
            timeout=8.0,
        )
    except TimeoutError:
        pytest.skip("tool-trends no responde RPC (¿AMQP_ENABLED o RabbitMQ?)")

    assert reply.ok, reply.error
    result = reply.payload.get("result") or {}
    # tolera que el handler devuelva data directa o un envelope
    data = result.get("data", result) if isinstance(result, dict) else result
    assert data["count"] >= 1
