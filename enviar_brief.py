"""
Envía un brief personalizado al sistema.
Uso: python enviar_brief.py "Tu brief aquí" [client_id]
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pika

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
RABBITMQ_USER = "user"
RABBITMQ_PASS = "password"


def enviar_brief(content: str, client_id: int = 1):
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
    ch.basic_publish(exchange="", routing_key="ideation_queue", body=json.dumps(brief))
    conn.close()

    print(f"[ENVIADO] client_id={client_id}")
    print(f"[BRIEF]   {content}")
    print()
    print("Espera ~15-30s y luego consulta:")
    print("  docker exec proyectomultiagente-postgres-1 psql -U postgres -d ideation_db -c \"SELECT id, LEFT(content,120) FROM ideas_generadas ORDER BY id DESC LIMIT 3;\"")


if __name__ == "__main__":
    brief = sys.argv[1] if len(sys.argv) > 1 else (
        "Create a social media campaign for a new coffee shop opening in Madrid"
    )
    client_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    enviar_brief(brief, client_id)
