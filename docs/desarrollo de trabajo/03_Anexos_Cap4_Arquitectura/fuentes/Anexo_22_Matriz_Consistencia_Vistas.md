# Anexo 22. Matriz de Correspondencia y Consistencia entre Vistas (C4 ↔ Gaia ↔ AUML)

<div class="meta">
<b>Capítulo:</b> 4 (Definición y Evaluación de Arquitectura) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE3 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Justificación de la Triangulación de Vistas Arquitectónicas

Los sistemas multiagente basados en microservicios requieren múltiples niveles de abstracción para representar tanto la topología de red y despliegue físico como las dinámicas conversacionales y los roles cognitivos. Para garantizar la consistencia sistémica y evitar discrepancias entre el diseño estructural y el comportamiento de los agentes, se integraron tres marcos de modelado:

1. **Modelo C4 (Niveles 1 a 4):** Modela la infraestructura física, los contenedores y los componentes de software.
2. **Metodología Gaia:** Modela la organización multiagente mediante roles, permisos, responsabilidades y lectura BDI (Beliefs, Desires, Intentions).
3. **AUML (Agent Unified Modeling Language):** Modela los protocolos de comunicación e intercambio de mensajes interactivos (FIPA-ACL) entre el orquestador y los agentes.

---

## 2. Matriz de Consistencia y Correspondencia entre Vistas

La siguiente matriz certifica la correspondencia unívoca entre cada contenedor C4 desplegado, su puerto de red, su rol formal en la metodología Gaia y los eventos AUML que consume y emite:

| Contenedor C4 Nivel 2 | Puerto | Clasificacion Funcional | Rol Gaia | Mensajes y Eventos AUML |
| --- | --- | --- | --- | --- |
| orchestrator | 8002 | Coordinacion y Supervision | Supervisor | agent.task.triggered (request) / agent.task.completed (inform) |
| agente-ideacion | 8000 | Agente Autonomo (Worker) | Ideator | Consume agent.ideacion.tasks / Emite agent.task.completed |
| agente-publicacion | 8001 | Agente Autonomo (Worker) | Publisher | Consume agent.publicacion.tasks / Emite agent.task.completed |
| llm-gateway | 8003 | Pasarela de Inteligencia | Servicio Invocado | HTTP POST /v1/generate / HTTP POST /v1/embeddings |
| tool-client | 8010 | Herramienta TaaS | Servicio Invocado | Manifiesto JSON + GET /profile/{id} |
| tool-trends | 8011 | Herramienta TaaS | Servicio Invocado | Manifiesto JSON + POST /query |
| tool-competitors | 8012 | Herramienta TaaS | Servicio Invocado | Manifiesto JSON + POST /references |
| tool-rag | 8013 | Herramienta TaaS | Servicio Invocado | Manifiesto JSON + POST /ideas / POST /search |
| tool-news | 8014 | Herramienta TaaS | Servicio Invocado | Manifiesto JSON + GET /news |
| tool-trending | 8015 | Herramienta TaaS | Servicio Invocado | Manifiesto JSON + GET /topics |
| tool-postiz | 8016 | Herramienta TaaS | Servicio Invocado | Manifiesto JSON + POST /publish |
| rabbitmq | 5672 | Infraestructura de Mensajeria | Infraestructura | AMQP 0-9-1 Connection / Channels / Durable Queues |
| postgres | 5432 | Infraestructura de Persistencia | Infraestructura | SQL DDL/DML + Extension pgvector (vector 768) |
| redis | 6379 | Infraestructura de Estado | Infraestructura | RedisJSON / Hashes / Checkpoints LangGraph |
| frontend-bff | 3000 | Presentacion y Fachada | Presentacion | HTTP REST + Server-Sent Events (SSE) |


---

## 3. Conclusiones de Consistencia Arquitectónica

1. **Trazabilidad 1:1:** Cada uno de los 14 servicios contenerizados en Docker cuenta con una función asignada en Gaia y un protocolo de interacción definido en AUML.
2. **Desacoplamiento Estricto:** Los agentes autónomos (Ideator y Publisher) no se comunican directamente entre sí por HTTP síncrono, sino que interactúan asíncronamente a través del Supervisor mediante colas durables en RabbitMQ, asegurando que fallos en un agente no bloqueen la totalidad del sistema.
