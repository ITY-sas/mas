# Prueba de Concepto de Sistema Multi-Agente Basado en Microservicios

## Arquitectura de la PoC

[Diagrama en Mermaid]

## Implementación y No Implementación

- **Implementado**:
  - Agente de Ideación
  - Agente de Publicación
  - RabbitMQ
  - PostgreSQL con extensión pgvector
  - Un único proveedor LLM local (Ollama)

- **No Implementado**:
  - Agente de Edición
  - API Gateway, Vault, MinIO, Prometheus/Grafana, ELK, Jaeger
  - Fuentes de datos externas reales
  - Cadena de fallback multi-proveedor de LLM

## Levantamiento del Sistema

Ejecuta el siguiente comando en la raíz del proyecto:

