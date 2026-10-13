import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from common.events import Event
import agente_ideacion.main as ideacion_main
import agente_publicacion.main as publicacion_main

pytestmark = pytest.mark.unit

def test_ideacion_main_endpoints():
    client = TestClient(ideacion_main.app)
    
    # /health
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["agent"] == "ideacion"
    assert res.json()["status"] == "healthy"
    
    # /metrics
    res = client.get("/metrics")
    assert res.status_code == 200
    assert res.json()["agent"] == "ideacion"
    
    # /tools
    res = client.get("/tools")
    assert res.status_code == 200
    assert res.json()["agent"] == "ideacion"

def test_ideacion_main_task_state():
    client = TestClient(ideacion_main.app)
    
    # Graph None -> 503
    old_graph = ideacion_main.GRAPH
    try:
        ideacion_main.GRAPH = None
        res = client.get("/state/task-123")
        assert res.status_code == 503
        
        # Fake graph empty state -> 404
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = None
        ideacion_main.GRAPH = mock_graph
        res = client.get("/state/task-123")
        assert res.status_code == 404
        
        # Fake graph with values -> 200
        snap = MagicMock()
        snap.values = {"idea": "Super Idea"}
        snap.next = ()
        mock_graph.get_state.return_value = snap
        res = client.get("/state/task-123")
        assert res.status_code == 200
        assert res.json()["values"]["idea"] == "Super Idea"
    finally:
        ideacion_main.GRAPH = old_graph

def test_ideacion_handle_triggered():
    old_graph = ideacion_main.GRAPH
    try:
        mock_graph = MagicMock()
        ideacion_main.GRAPH = mock_graph
        
        # Missing task_id
        ev = Event(event_type="agent.task.triggered", task_id="", payload={})
        ideacion_main.handle_triggered(ev)
        
        # Missing client_id
        with patch("agente_ideacion.main.publish_event") as mock_pub:
            ev = Event(event_type="agent.task.triggered", task_id="task-1", payload={})
            ideacion_main.handle_triggered(ev)
            assert mock_pub.called
            assert mock_pub.call_args[0][1].status == "failed"
            
        # Success path
        with patch("agente_ideacion.main.run_agent_task") as mock_runner, \
             patch("agente_ideacion.main.publish_event") as mock_pub:
            mock_runner.return_value = {"idea": "Idea 1", "idea_id": 10, "preproduction": {}}
            ev = Event(
                event_type="agent.task.triggered",
                task_id="task-2",
                payload={"client_id": 1, "brand_id": 1, "brief": {"content": "Test"}}
            )
            ideacion_main.handle_triggered(ev)
            assert mock_pub.called
            assert mock_pub.call_args[0][1].status == "completed"
            
        # Exception in runner
        with patch("agente_ideacion.main.run_agent_task", side_effect=RuntimeError("Graph crash")), \
             patch("agente_ideacion.main.publish_event") as mock_pub:
            ev = Event(
                event_type="agent.task.triggered",
                task_id="task-3",
                payload={"client_id": 1, "brand_id": 1}
            )
            ideacion_main.handle_triggered(ev)
            assert mock_pub.called
            assert mock_pub.call_args[0][1].status == "failed"
    finally:
        ideacion_main.GRAPH = old_graph

def test_publicacion_main_endpoints():
    client = TestClient(publicacion_main.app)
    
    # /health
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["agent"] == "publicacion"
    assert res.json()["status"] == "healthy"
    
    # /metrics
    res = client.get("/metrics")
    assert res.status_code == 200
    assert res.json()["agent"] == "publicacion"
    
    # /tools
    res = client.get("/tools")
    assert res.status_code == 200
    assert res.json()["agent"] == "publicacion"

def test_publicacion_main_task_state():
    client = TestClient(publicacion_main.app)
    
    old_graph = publicacion_main.GRAPH
    try:
        publicacion_main.GRAPH = None
        res = client.get("/state/task-123")
        assert res.status_code == 503
        
        mock_graph = MagicMock()
        mock_graph.get_state.return_value = None
        publicacion_main.GRAPH = mock_graph
        res = client.get("/state/task-123")
        assert res.status_code == 404
        
        snap = MagicMock()
        snap.values = {"publication": "Super Post"}
        snap.next = ()
        mock_graph.get_state.return_value = snap
        res = client.get("/state/task-123")
        assert res.status_code == 200
        assert res.json()["values"]["publication"] == "Super Post"
    finally:
        publicacion_main.GRAPH = old_graph

def test_publicacion_handle_triggered():
    old_graph = publicacion_main.GRAPH
    try:
        mock_graph = MagicMock()
        publicacion_main.GRAPH = mock_graph
        
        # Missing task_id
        ev = Event(event_type="agent.task.triggered", task_id="", payload={})
        publicacion_main.handle_triggered(ev)
        
        # Missing client_id
        with patch("agente_publicacion.main.publish_event") as mock_pub:
            ev = Event(event_type="agent.task.triggered", task_id="task-1", payload={})
            publicacion_main.handle_triggered(ev)
            assert mock_pub.called
            assert mock_pub.call_args[0][1].status == "failed"
            
        # Success path
        with patch("agente_publicacion.main.run_agent_task") as mock_runner, \
             patch("agente_publicacion.main.publish_event") as mock_pub:
            mock_runner.return_value = {"publication": "Post 1", "publication_id": 20, "publication_variants": []}
            ev = Event(
                event_type="agent.task.triggered",
                task_id="task-2",
                payload={"client_id": 1, "brand_id": 1, "idea": "Idea test"}
            )
            publicacion_main.handle_triggered(ev)
            assert mock_pub.called
            assert mock_pub.call_args[0][1].status == "completed"
            
        # Exception in runner
        with patch("agente_publicacion.main.run_agent_task", side_effect=RuntimeError("Graph crash")), \
             patch("agente_publicacion.main.publish_event") as mock_pub:
            ev = Event(
                event_type="agent.task.triggered",
                task_id="task-3",
                payload={"client_id": 1, "brand_id": 1}
            )
            publicacion_main.handle_triggered(ev)
            assert mock_pub.called
            assert mock_pub.call_args[0][1].status == "failed"
    finally:
        publicacion_main.GRAPH = old_graph

def test_agent_retry_and_build_graph():
    # Test _retry success
    res = ideacion_main._retry("test", lambda: 42, attempts=2, delay=0.01)
    assert res == 42
    
    # Test _retry failure
    with pytest.raises(RuntimeError):
        def failing():
            raise ValueError("boom")
        ideacion_main._retry("test_fail", failing, attempts=2, delay=0.01)
        
    # Test _build_graph for ideacion
    with patch("langgraph.checkpoint.redis.RedisSaver") as mock_saver, \
         patch("agente_ideacion.main.create_ideacion_graph") as mock_create:
        g = ideacion_main._build_graph()
        assert mock_saver.called
        assert mock_create.called
        
    # Test _build_graph for publicacion
    with patch("langgraph.checkpoint.redis.RedisSaver") as mock_saver, \
         patch("agente_publicacion.main.create_publicacion_graph") as mock_create:
        g = publicacion_main._build_graph()
        assert mock_saver.called
        assert mock_create.called
