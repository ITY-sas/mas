
## Decisiones Técnicas Tomadas

- Se utilizó FastAPI para exponer endpoints de observabilidad (`/health` y `/metrics`).
- Se implementó un grafo de deliberación básico en cada agente.
- Se utilizó PostgreSQL con la extensión `pgvector` para la memoria semántica.
- Se utilizó RabbitMQ como bus de mensajes asíncrono entre agentes.
- Se implementó un catálogo de tools en cada agente.
