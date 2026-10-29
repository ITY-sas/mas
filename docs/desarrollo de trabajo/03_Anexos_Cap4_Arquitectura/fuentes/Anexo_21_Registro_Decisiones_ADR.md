# Anexo 21. Registro de Decisiones de Arquitectura (ADR-001 a ADR-008)

<div class="meta">
<b>Capítulo:</b> 4 (Definición y Evaluación de Arquitectura) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE3 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Introducción al Registro ADR (Architecture Decision Records)

El diseño de software sustentable requiere documentar formalmente las decisiones arquitectónicas clave, explicitando el contexto de negocio, las opciones tecnológicas contrastadas, las razones de la elección y sus consecuencias operativas.

El sistema multiagente de ITY SAS se rige por ocho Decisiones de Arquitectura (ADR-001 a ADR-008):

---

## 2. Catálogo Consolidado de ADRs

### ADR-001: Estilo Arquitectónico Híbrido (Microservicios + AMQP + LangGraph)
* **Estado:** Aceptado e Implementado.
* **Contexto:** Se requiere orquestar procesos cognitivos no deterministas con transacciones seguras de negocio.
* **Decisión:** Desacoplar el sistema en 14 microservicios contenerizados comunicados por colas de eventos AMQP y REST, utilizando LangGraph para el control de grafos deliberativos.
* **Consecuencias:** Alta resiliencia y modularidad; mayor complejidad inicial de infraestructura Docker.

### ADR-002: Message Broker RabbitMQ frente a Apache Kafka
* **Estado:** Aceptado e Implementado.
* **Contexto:** Necesidad de enrutar mensajes asíncronos entre el orquestador y los agentes de software.
* **Decisión:** Adoptar RabbitMQ 3.13 con protocolo AMQP 0-9-1 y colas durables con acuse manual (`basic_ack`).
* **Consecuencias:** Configuración ligera y excelente soporte de patrones de mensajería RPC y colas de trabajo; Kafka se descartó por requerir un consumo innecesario de memoria en despliegues medianos.

### ADR-003: LangGraph para la Deliberación de Agentes
* **Estado:** Aceptado e Implementado.
* **Contexto:** Los agentes deben tomar decisiones cíclicas, reintentar ante fallos de formato y mantener memoria.
* **Decisión:** Utilizar LangGraph en Python para modelar los agentes como grafos cíclicos de estados con checkpointer persistente.
* **Consecuencias:** Trazabilidad paso a paso de cada nodo cognitivo; control total del flujo frente a agentes de caja negra.

### ADR-004: Ingesta de Tendencias mediante RSS y Scraping Ético
* **Estado:** Aceptado e Implementado.
* **Contexto:** Las APIs comerciales de redes sociales (TikTok/Meta) imponen cuotas de pago restrictivas para una pyme.
* **Decisión:** Implementar un microservicio de herramientas (`tool-trends`) que agregue Google News RSS, feeds temáticos y datos públicos.
* **Consecuencias:** Autonomía operativa a costo marginal cero; menor profundidad en métricas privadas de competidores.

### ADR-005: LLM Gateway Centralizado Multi-Proveedor
* **Estado:** Aceptado e Implementado.
* **Contexto:** Riesgo de interrupción por fallos de cuota o caídas de servidores LLM locales.
* **Decisión:** Implementar una pasarela centralizada en FastAPI con conmutación automática (*fallback*) de modelo primario a secundario y caché semántica en Redis.
* **Consecuencias:** Transparencia total para los agentes y disponibilidad continua ante saturación del hardware host.

### ADR-006: Persistencia Híbrida en PostgreSQL con pgvector
* **Estado:** Aceptado e Implementado.
* **Contexto:** Necesidad de unificar datos transaccionales relacionales y memoria semántica vectorial.
* **Decisión:** Utilizar PostgreSQL 16 con la extensión oficial `pgvector` para almacenar embeddings de 768 dimensiones en la misma base de datos.
* **Consecuencias:** Se eliminó la necesidad de operar una base de datos vectorial dedicada (Pinecone/Milvus), reduciendo la sobrecarga operativa y garantizando integridad referencial ACID.

### ADR-007: Observabilidad Integrada con TaskStore y SPA
* **Estado:** Aceptado e Implementado.
* **Contexto:** El equipo creativo y administrativo requiere visibilidad en tiempo real del avance de los agentes.
* **Decisión:** Implementar una base de tareas en memoria sincronizada con el frontend SPA en React 19 mediante endpoints REST y WebSockets.
* **Consecuencias:** Monitoreo transparente sin sobrecargar los motores de base de datos relacionales.

### ADR-008: Compuerta Humana Obligatoria (HITL) y Guarda de Inmutabilidad
* **Estado:** Aceptado e Implementado.
* **Contexto:** Exigencia ética irrenunciable de los directivos de ITY SAS de no publicar contenido sin visto bueno humano.
* **Decisión:** Configurar una guarda determinista a nivel de API (`/api/v1/publications/{id}/deliver`) que retorna **HTTP 409 Conflict** si la publicación no cuenta con el estatus `approved` y el ID del revisor.
* **Consecuencias:** Blindaje ético absoluto contra publicaciones no deseadas; verificación empírica aprobada al 100% en las pruebas unitarias.
