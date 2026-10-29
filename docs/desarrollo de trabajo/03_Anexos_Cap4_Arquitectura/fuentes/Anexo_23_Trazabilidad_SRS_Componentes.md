# Anexo 23. Matriz de Trazabilidad Requisitos (SRS) ↔ Componentes Arquitectónicos

<div class="meta">
<b>Capítulo:</b> 4 (Definición y Evaluación de Arquitectura) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE3 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Propósito de la Asignación Arquitectónica de Requerimientos

La matriz de trazabilidad entre los Requisitos de Software (SRS IEEE 830) y los Componentes Arquitectónicos tiene como objetivo validar que todos los 49 requerimientos del sistema (30 funcionales, 9 no funcionales y 10 interfaces externas) se encuentren plenamente asignados a componentes de software concretos y testeables en la pila contenerizada.

---

## 2. Matriz Completa de Trazabilidad Requisito ↔ Componente (49 Requisitos)

| ID | Nombre | Prioridad | Macro_Issue | Componente_Asignado |
| --- | --- | --- | --- | --- |
| REQ-F01 | Consulta de tendencias activas | Must | REQ-US001 | tool-trends / tool-trending |
| REQ-F02 | Brief estructurado | Must | REQ-US001 | agente-ideacion / tool-client |
| REQ-F03 | Validacion semantica de brief | Should | REQ-US001 | agente-ideacion / llm-gateway |
| REQ-F04 | Sugerencia de formato | Could | REQ-US001 | agente-ideacion |
| REQ-F05 | Rendimiento historico de cuenta | Should | REQ-US001 | tool-rag / tool-client |
| REQ-F06 | Extraccion de palabras clave | Should | REQ-US001 | agente-ideacion / llm-gateway |
| REQ-F07 | Alineacion con tono de marca | Could | REQ-US001 | tool-rag / agente-ideacion |
| REQ-F08 | Recuperacion de referentes | Should | REQ-US001 | tool-competitors / tool-rag |
| REQ-F09 | Sugerencia de KPIs esperados | Could | REQ-US001 | agente-ideacion |
| REQ-F10 | Retroalimentacion humana (HITL) | Must | REQ-US001 | frontend-bff / orchestrator |
| REQ-F11 | Validacion tecnica de video | Must | REQ-US002 | agente-ideacion (nodo QC) |
| REQ-F12 | Limite forzoso de revisiones | Must | REQ-US002 | orchestrator / frontend-bff |
| REQ-F13 | Rough cut automatico | Should | REQ-US002 | agente-ideacion |
| REQ-F14 | Historial de retrabajo de editor | Should | REQ-US002 | frontend-bff / orchestrator |
| REQ-F15 | Subtitulos automaticos ASR | Must | REQ-US002 | tool-client / llm-gateway |
| REQ-F16 | Analisis del ritmo de edicion | Could | REQ-US002 | agente-ideacion |
| REQ-F17 | Generacion de proxy liviano | Could | REQ-US002 | tool-client |
| REQ-F18 | Correccion de color por histograma | Should | REQ-US002 | agente-ideacion |
| REQ-F19 | Notificacion por mensajeria | Should | REQ-US002 | orchestrator |
| REQ-F20 | Estimacion de tiempo restante | Could | REQ-US002 | frontend-bff / orchestrator |
| REQ-F21 | Adaptacion de relacion de aspecto | Must | REQ-US003 | agente-publicacion |
| REQ-F22 | Generacion de copy por canal | Must | REQ-US003 | agente-publicacion / llm-gateway |
| REQ-F23 | Integracion con scheduling (Postiz) | Must | REQ-US003 | tool-postiz / agente-publicacion |
| REQ-F24 | Previsualizacion en dispositivo | Should | REQ-US003 | frontend-bff |
| REQ-F25 | Generacion inteligente hashtags | Should | REQ-US003 | tool-trending / publisher |
| REQ-F26 | Recomendacion de mejor horario | Could | REQ-US003 | tool-client / publisher |
| REQ-F27 | Generacion miniatura de portada | Could | REQ-US003 | agente-publicacion |
| REQ-F28 | Validacion limites de caracteres | Must | REQ-US003 | agente-publicacion |
| REQ-F29 | Informe consolidado de entrega | Should | REQ-US003 | frontend-bff / orchestrator |
| REQ-F30 | Tolerancia a fallos y reintentos | Must | REQ-US003 | common/events.py / tool-postiz |
| REQ-NF01 | Contenedorizacion independiente | Must | REQ-US004 | docker-compose.yml / Dockerfiles |
| REQ-NF02 | Latencia inter-microservicios | Must | REQ-US004 | Red Docker multiagent-net |
| REQ-NF03 | Disponibilidad del servicio | Should | REQ-US004 | Docker healthchecks |
| REQ-NF04 | Cifrado y gestion de secretos | Must | REQ-US004 | .env / HashiCorp Vault |
| REQ-NF05 | Escalabilidad horizontal | Should | REQ-US004 | RabbitMQ colas durables |
| REQ-NF06 | Auditoria y trazabilidad | Should | REQ-US004 | Redis TaskStore / chat_history |
| REQ-NF07 | Fiabilidad y fallback LLM | Could | REQ-US004 | llm_gateway/resilience.py |
| REQ-NF08 | Tiempo de arranque de servicios | Should | REQ-US004 | FastAPI / Uvicorn |
| REQ-NF09 | Cumplimiento Ley 1581 de 2012 | Must | REQ-US004 | Esquemas PostgreSQL |
| REQ-IE01 | API TikTok Research v2 | Must | REQ-US001 | tool-news / tool-trending |
| REQ-IE02 | API Instagram Graph v21.0 | Must | REQ-US001 | tool-trends |
| REQ-IE03 | Motor FFmpeg 6.1 / OpenCV | Must | REQ-US002 | agente-ideacion (validate_dossier) |
| REQ-IE04 | LLM Gateway Service (:8003) | Must | REQ-US001 | llm-gateway |
| REQ-IE05 | API Postiz / Metricool | Must | REQ-US003 | tool-postiz |
| REQ-IE06 | HashiCorp Vault (:8200) | Should | REQ-US004 | Infraestructura de secretos |
| REQ-IE07 | WhatsApp / Slack Webhooks | Should | REQ-US002 | orchestrator / frontend-bff |
| REQ-IE08 | Google YouTube Data API v3 | Should | REQ-US003 | tool-postiz |
| REQ-IE09 | Prometheus Metrics Exporter | Should | REQ-US004 | Endpoints /health y /metrics |
| REQ-IE10 | MinIO S3 Object Storage (:9000) | Could | REQ-US002 | Volumenes persistentes Docker |


---

## 3. Conclusiones de Cobertura de Requerimientos

1. **Asignación del 100%:** Los 49 requisitos cuentan con al menos un componente asignado responsable de su cumplimiento.
2. **Módulos de Mayor Densidad:** El Agente de Ideación concentra 10 requisitos funcionales y 4 interfaces, mientras que el Agente de Publicación y el Orquestador concentran la ejecución de 11 requisitos y las guardas de calidad (ADR-008).
