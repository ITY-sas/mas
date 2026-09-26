"""
Prueba end-to-end de la arquitectura de microservicios multi-agente.

Valida de punta a punta:

  1. Salud de la pila y Tool Discovery (6 manifiestos → endpoints).
  2. `POST /process` del orquestador **stateless**: ciclo
     interrupt() → agent.task.triggered → agente → agent.task.completed →
     Command(resume=...) hasta completar ideación + publicación.
  3. Persistencia en PostgreSQL (ideas_generadas / publicaciones_generadas).
  4. Estado EXTERNO del proceso:
       · metadatos y resultados → TaskStore en Redis (GET /tasks/{id})
       · historial de chat      → PostgreSQL  (GET /tasks/{id}/history)
       · checkpoint del agente  → Redis       (GET /state/{id} en el agente)
  5. (opcional `--eventos`) ingreso de briefs por RabbitMQ (ideation_queue).

Requisitos:
  - `docker compose up -d --build`
  - Ollama en 127.0.0.1:11434 con los modelos configurados (.env)
  - Dependencias: pip install requests psycopg2-binary pika

Uso:
  python prueba_e2e.py            # flujo HTTP
  python prueba_e2e.py --eventos  # + ingreso por eventos RabbitMQ
"""
import argparse
import json
import sys
import time

# Fix encoding en Windows (emojis, tildes)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ORQUESTADOR = "http://localhost:8002"
AGENTE_IDEACION = "http://localhost:8000"

POSTGRES_CFG = dict(
    host="localhost",
    port=5432,
    database="ideation_db",
    user="postgres",
    password="password",
)
WAIT_SECONDS = 600  # el orquestador espera por eventos + 2 LLM


# ── 1. Salud + Tool Discovery ──────────────────────────────────
def check_stack() -> bool:
    import requests

    print("[1/5] Salud de la pila …")
    try:
        health = requests.get(f"{ORQUESTADOR}/health", timeout=5).json()
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] orquestador inaccesible: {exc}")
        print("         ¿docker compose up -d --build?")
        return False

    for name, state in health.get("subsystems", {}).items():
        mark = "OK " if state == "ok" else "!! "
        print(f"  {mark}{name}: {state}")
    if health.get("status") != "healthy":
        print("  [ERROR] subsistemas caídos — levántalos antes de continuar")
        return False

    tools = requests.get(f"{ORQUESTADOR}/tools", timeout=10)
    if tools.status_code != 200:
        print(f"  [ERROR] Tool Discovery falló: {tools.text[:200]}")
        return False
    names = sorted(t["tool"] for t in tools.json()["tools"])
    print(f"  [OK ] Tool Discovery ({len(names)}): {', '.join(names)}")
    if len(names) < 6:
        return False
    return True


# ── 2. Pipeline vía HTTP ───────────────────────────────────────
def run_pipeline_http(client_id: int, brief: str) -> dict:
    import requests

    print("\n[2/5] POST /process (orquestador stateless) …")
    started = time.time()
    try:
        resp = requests.post(
            f"{ORQUESTADOR}/process",
            json={"client_id": client_id, "content": brief,
                  "wait": True, "timeout": WAIT_SECONDS},
            timeout=WAIT_SECONDS + 60,
        )
    except requests.Timeout:
        print("  [ERROR] timeout esperando el pipeline")
        return {}

    elapsed = time.time() - started
    if resp.status_code != 200:
        print(f"  [ERROR] HTTP {resp.status_code}: {resp.text[:400]}")
        return {}

    data = resp.json()
    print(f"  [OK ] completado en {elapsed:.1f}s")
    print(f"         task_id        : {data['task_id']}")
    print(f"         idea_id        : {data['idea_id']}")
    print(f"         publication_id : {data['publication_id']}")
    for agent, info in data.get("agents", {}).items():
        print(f"         agente {agent:<11}: {info['status']}")
    return data


# ── 3. Verificación en PostgreSQL ──────────────────────────────
def verify_postgres(client_id: int, idea_id: int, publication_id: int) -> bool:
    import psycopg2

    print("\n[3/5] Verificación en PostgreSQL …")
    conn = psycopg2.connect(**POSTGRES_CFG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT content FROM ideas_generadas WHERE id=%s AND client_id=%s",
                (idea_id, client_id),
            )
            idea_row = cur.fetchone()
            cur.execute(
                "SELECT content FROM publicaciones_generadas "
                "WHERE id=%s AND client_id=%s",
                (publication_id, client_id),
            )
            pub_row = cur.fetchone()
    finally:
        conn.close()

    if not idea_row or not pub_row:
        print("  [ERROR] filas no encontradas en la BD")
        return False
    print(f"  [OK ] idea #{idea_id}: {idea_row[0][:100].replace(chr(10), ' ')}…")
    print(f"  [OK ] publicación #{publication_id}: "
          f"{pub_row[0][:100].replace(chr(10), ' ')}…")
    return True


# ── 4. Estado externo (Redis + PostgreSQL) ─────────────────────
def verify_external_state(task_id: str) -> bool:
    import requests

    print("\n[4/5] Estado EXTERNO al proceso …")
    ok = True

    # 4a. metadatos + resultados en TaskStore (Redis)
    task = requests.get(f"{ORQUESTADOR}/tasks/{task_id}", timeout=5)
    if task.status_code != 200 or task.json().get("status") != "completed":
        print(f"  [ERROR] TaskStore: {task.text[:200]}")
        ok = False
    else:
        print("  [OK ] TaskStore (Redis): status=completed con resultados")

    # 4b. historial de chat durable (PostgreSQL)
    history = requests.get(f"{ORQUESTADOR}/tasks/{task_id}/history", timeout=5)
    if history.status_code != 200:
        print(f"  [ERROR] historial de chat: {history.text[:200]}")
        ok = False
    else:
        messages = history.json()["messages"]
        roles = [m["role"] for m in messages]
        print(f"  [OK ] historial de chat (PostgreSQL): {roles}")
        if not roles or roles[0] != "user" or roles[-1] != "assistant":
            print("  [ERROR] turnos inesperados en el historial")
            ok = False

    # 4c. checkpoint del agente en Redis (visible desde OTRO proceso)
    state = requests.get(f"{AGENTE_IDEACION}/state/{task_id}", timeout=5)
    if state.status_code != 200:
        print(f"  [ERROR] checkpoint del agente: {state.text[:200]}")
        ok = False
    else:
        body = state.json()
        print(f"  [OK ] checkpoint agente ideación (thread={body['thread_id']}): "
              f"idea_id={body['values'].get('idea_id')}, "
              f"pendientes={body['pending_nodes']}")
    return ok


# ── 5. (opcional) Ingreso de briefs por eventos ────────────────
def run_event_ingress(client_id: int, brief: str, timeout: int = 240) -> bool:
    import pika
    import psycopg2

    print(f"\n[5/5] Ingreso por eventos (ideation_queue, client_id={client_id}) …")
    try:
        conn = pika.BlockingConnection(
            pika.ConnectionParameters(
                host="localhost", port=5672,
                credentials=pika.PlainCredentials("user", "password"),
            )
        )
        ch = conn.channel()
        ch.queue_declare(queue="ideation_queue", durable=True)
        ch.basic_publish(
            exchange="", routing_key="ideation_queue",
            body=json.dumps({"client_id": client_id, "content": brief}),
        )
        conn.close()
        print("  [OK ] brief publicado en ideation_queue")
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] publicación falló: {exc}")
        return False

    print(f"  esperando idea en PostgreSQL (máx {timeout}s) …")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            db = psycopg2.connect(**POSTGRES_CFG)
            with db.cursor() as cur:
                cur.execute(
                    "SELECT id FROM ideas_generadas WHERE client_id=%s ORDER BY id DESC LIMIT 1",
                    (client_id,),
                )
                row = cur.fetchone()
            db.close()
        except Exception:  # noqa: BLE001
            row = None
        if row:
            print(f"  [OK ] evento procesado → nueva idea #{row[0]} (client_id={client_id})")
            return True
        time.sleep(3)
    print("  [ERROR] el evento no generó resultados")
    return False


# ── Main ───────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="E2E multi-servicio")
    parser.add_argument("--eventos", action="store_true",
                        help="añade el ingreso de briefs por RabbitMQ")
    args = parser.parse_args()

    client_id = 99
    brief = "Create a launch campaign for a new eco-friendly water bottle"

    print("=" * 64)
    print("PRUEBA E2E – Arquitectura multi-servicio de agentes")
    print("=" * 64)

    if not check_stack():
        sys.exit(1)

    data = run_pipeline_http(client_id, brief)
    if not data:
        sys.exit(1)

    ok_pg = verify_postgres(client_id, data["idea_id"], data["publication_id"])
    ok_state = verify_external_state(data["task_id"])

    ok_events = True
    if args.eventos:
        ok_events = run_event_ingress(98, "Brief llegado por eventos AMQP")

    ok = ok_pg and ok_state and ok_events
    print("\n" + "=" * 64)
    if ok:
        print("✅ PRUEBA EXITOSA – pipeline, tools, gateway y estado externo OK")
    else:
        print("⚠️  PRUEBA INCOMPLETA – revisa los puntos marcados con [ERROR]")
        print("   docker compose logs orchestrator agente-ideacion llm-gateway")
    print("=" * 64)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
