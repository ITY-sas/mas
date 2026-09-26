"""
Prueba end-to-end del sistema multi-agente.

Flujo que valida:
  1. Publica un brief en ideation_queue (RabbitMQ).
  2. El agente de ideación genera una idea (Ollama) y la guarda en PostgreSQL.
  3. El agente de publicación recibe la idea, genera una publicación (Ollama)
     y la guarda en PostgreSQL.
  4. Verifica que ambas filas existan en la base de datos.

Requisitos:
  - docker compose levantado (rabbitmq, postgres, ollama, agentes)
  - Modelo de Ollama descargado:  docker exec ollama ollama pull llama3.2:1b
  - Dependencias:  pip install pika psycopg2-binary
"""

import json
import sys
import time

# Fix encoding en Windows (emojis, tildes)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pika
import psycopg2

# ── Configuración ──────────────────────────────────────────────
RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USER = "user"
RABBITMQ_PASS = "password"
POSTGRES_CFG = dict(
    host="localhost",
    port=5432,
    database="ideation_db",
    user="postgres",
    password="password",
)
WAIT_SECONDS = 60  # tiempo máximo de espera (Ollama puede tardar)


# ── 1. Publicar brief ──────────────────────────────────────────
def publish_brief(client_id: int, content: str):
    conn = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            port=RABBITMQ_PORT,
            credentials=pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS),
        )
    )
    ch = conn.channel()
    ch.queue_declare(queue="ideation_queue")

    brief = {"client_id": client_id, "content": content}
    ch.basic_publish(
        exchange="",
        routing_key="ideation_queue",
        body=json.dumps(brief),  # JSON válido (antes era str(dict))
    )
    conn.close()
    print(f"[OK] Brief publicado en ideation_queue: {brief}")


# ── 2. Consultar resultados ────────────────────────────────────
def get_ideas(client_id: int) -> list[dict]:
    conn = psycopg2.connect(**POSTGRES_CFG)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, content FROM ideas_generadas WHERE client_id=%s ORDER BY id",
            (client_id,),
        )
        return [{"id": r[0], "content": r[1]} for r in cur.fetchall()]
    finally:
        conn.close()


def get_publicaciones(client_id: int) -> list[dict]:
    conn = psycopg2.connect(**POSTGRES_CFG)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, idea_id, content FROM publicaciones_generadas "
            "WHERE client_id=%s ORDER BY id",
            (client_id,),
        )
        return [{"id": r[0], "idea_id": r[1], "content": r[2]} for r in cur.fetchall()]
    finally:
        conn.close()


# ── 3. Esperar resultados ──────────────────────────────────────
def wait_for_results(client_id: int, timeout: int = WAIT_SECONDS):
    print(f"\nEsperando resultados (máx {timeout}s) …")
    deadline = time.time() + timeout
    while time.time() < deadline:
        ideas = get_ideas(client_id)
        pubs = get_publicaciones(client_id)
        if ideas and pubs:
            return ideas, pubs
        time.sleep(3)
    return get_ideas(client_id), get_publicaciones(client_id)


# ── Main ───────────────────────────────────────────────────────
def main():
    client_id = 99
    brief = "Create a launch campaign for a new eco-friendly water bottle"

    print("=" * 60)
    print("PRUEBA E2E – Sistema Multi-Agente")
    print("=" * 60)

    # Paso 1: publicar
    try:
        publish_brief(client_id, brief)
    except Exception as exc:
        print(f"[ERROR] No se pudo publicar el brief: {exc}")
        print("¿Está Docker levantado?  docker compose up -d --build")
        sys.exit(1)

    # Paso 2: esperar ideas + publicaciones
    ideas, pubs = wait_for_results(client_id)

    # Paso 3: informe
    print("\n" + "=" * 60)
    print("RESULTADOS")
    print("=" * 60)

    print(f"\nIdeas generadas ({len(ideas)}):")
    for i in ideas:
        preview = i["content"][:140].replace("\n", " ")
        print(f"  #{i['id']}: {preview}…")

    print(f"\nPublicaciones generadas ({len(pubs)}):")
    for p in pubs:
        preview = p["content"][:140].replace("\n", " ")
        print(f"  #{p['id']} (idea_id={p['idea_id']}): {preview}…")

    ok = bool(ideas) and bool(pubs)
    print("\n" + "=" * 60)
    if ok:
        print("✅ PRUEBA EXITOSA – Flujo completo de punta a punta")
    else:
        print("⚠️  PRUEBA INCOMPLETA – Faltan resultados")
        print("   Posibles causas:")
        print("   - Ollama sin modelo: docker exec ollama ollama pull llama3.2:1b")
        print("   - Agentes caídos:     docker compose logs agente-ideacion")
        print("   - Tiempo insuficiente (aumenta WAIT_SECONDS)")
    print("=" * 60)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
