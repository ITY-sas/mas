"""
Prueba de la API del orquestador stateless (ejecutar desde la raíz).

Demuestra los tres modos de uso del orquestador microservicio:

  1. `GET /health`     → estado de subsistemas (Redis, RabbitMQ, PG, gateway)
  2. `GET /graph`      → descripción del grafo supervisor (interrupt/eventos)
  3. `GET /tools`      → catálogo agregado por Tool Discovery
  4. `POST /process` en modo ASÍNCRONO (`wait=false`) → task_id
  5. `GET /tasks/{id}` → metadatos/resultados (TaskStore en Redis),
     consultados desde OTRO proceso (el orquestador no retiene estado)
  6. `GET /tasks/{id}/history` → historial de chat durable (PostgreSQL)

Requisitos: `docker compose up -d --build` y Ollama en 127.0.0.1:11434.
"""
import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://localhost:8002"
TIMEOUT = 600


def main() -> None:
    print("=" * 60)
    print("API del orquestador stateless")
    print("=" * 60)

    # 1. salud
    health = requests.get(f"{BASE}/health", timeout=5).json()
    print(f"\n[1] /health → {health['status']} ({health['agent']})")
    for name, state in health["subsystems"].items():
        print(f"      {name}: {state}")

    # 2. grafo
    graph = requests.get(f"{BASE}/graph", timeout=5).json()
    print(f"\n[2] /graph → nodos: {graph['nodes']}")
    print(f"      suspensión: {graph['suspension']}")
    print(f"      checkpointer: {graph['checkpointer']}")

    # 3. tool discovery
    try:
        tools = requests.get(f"{BASE}/tools", timeout=10)
        if tools.status_code == 200:
            names = [t["tool"] for t in tools.json()["tools"]]
            print(f"\n[3] /tools → {len(names)} descubiertas: {', '.join(names)}")
        else:
            print(f"\n[3] /tools → {tools.text[:200]}")
    except requests.RequestException as exc:
        print(f"\n[3] /tools → ERROR {exc}")

    # 4. lanzamiento asíncrono
    print("\n[4] POST /process (wait=false) …")
    try:
        resp = requests.post(
            f"{BASE}/process",
            json={
                "client_id": 1,
                "content": "Summer campaign for organic skincare",
                "wait": False,
            },
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [ERROR] {exc}")
        sys.exit(1)
    task_id = resp.json()["task_id"]
    print(f"  → task_id = {task_id} (estado en Redis, no en el proceso)")

    # 5. consulta de estado desde otro proceso
    print("\n[5] GET /tasks/{id} hasta completar …")
    deadline = time.time() + TIMEOUT
    task = {}
    while time.time() < deadline:
        task = requests.get(f"{BASE}/tasks/{task_id}", timeout=5).json()
        status = task.get("status")
        if status == "completed":
            break
        if status == "failed":
            print(f"  [ERROR] tarea fallida: {task.get('error')}")
            sys.exit(1)
        time.sleep(3)
    else:
        print("  [ERROR] timeout esperando la tarea")
        sys.exit(1)

    result = task.get("result", {})
    print(f"  → status = {task['status']}")
    print(f"    idea_id={result.get('idea_id')} "
          f"publication_id={result.get('publication_id')}")
    print(f"    agentes: "
          + ", ".join(f"{a}={v['status']}" for a, v in task["agents"].items()))

    # 6. historial de chat (PostgreSQL)
    history = requests.get(f"{BASE}/tasks/{task_id}/history", timeout=5)
    if history.status_code == 200:
        roles = [m["role"] for m in history.json()["messages"]]
        print(f"\n[6] /tasks/{{id}}/history → turnos: {roles}")
    else:
        print(f"\n[6] /tasks/{{id}}/history → {history.text[:200]}")

    print("\n" + "=" * 60)
    print("✅ Prueba del orquestador completada")
    print("=" * 60)


if __name__ == "__main__":
    main()
