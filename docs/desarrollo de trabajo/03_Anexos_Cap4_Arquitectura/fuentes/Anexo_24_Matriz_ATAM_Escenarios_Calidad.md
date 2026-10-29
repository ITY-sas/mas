# Anexo 24. Matriz ATAM de Escenarios de Calidad

<div class="meta">
<b>Capítulo:</b> 4 (Definición y Evaluación de Arquitectura) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE3 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Introducción a la Metodología ATAM

La evaluación de la arquitectura se formalizó mediante el método **ATAM** (*Architecture Tradeoff Analysis Method*) desarrollado por el Software Engineering Institute (SEI). ATAM permite evaluar la capacidad de la arquitectura diseñada para satisfacer atributos de calidad críticos en condiciones operativas extremas y escenarios de estrés.

---

## 2. Catálogo Oficial de Escenarios de Calidad Evaluados

| Código | Atributo de Calidad | Fuente del Estímulo | Estímulo | Entorno | Artefacto Afectado | Respuesta Esperada del Sistema | Medida de Respuesta |
|:---:|---|---|---|---|---|---|---|
| **QA-01** | **Rendimiento** | Community Manager | Envío de un brief estructurado solicitando 3 ángulos de contenido. | Operación normal con hardware host. | Agente de Ideación y LLM Gateway. | Generación de dossier completo con validación semántica. | Latencia total de inferencia $< 15,0$ s. |
| **QA-02** | **Disponibilidad** | Caída de infraestructura | Parada abrupta del servidor LLM local primario por sobrecarga. | Horario laboral con briefs en procesamiento. | LLM Gateway. | Detección de timeout ($>10$ s) y conmutación automática (*fallback*) al modelo secundario. | Continuidad operativa sin fallos visibles (HTTP 200). |
| **QA-03** | **Seguridad** | Intentos de inyección | Brief que incluye instrucciones para ignorar el tono de marca. | Operación regular. | Validador Pydantic del Agente de Ideación. | Rechazo o reparación en una sola pasada forzando el esquema tipado. | 100% de prompts maliciosos neutralizados. |
| **QA-04** | **Resiliencia** | Fallo de red / broker | Reinicio abrupto del contenedor de RabbitMQ durante la publicación. | Flujo de entrega en progreso. | Orquestador y Colas AMQP. | Persistencia de mensajes en volumen durable; reconexión y reanudación automática. | Cero pérdida de briefs o publicaciones en curso. |
| **QA-05** | **Integridad Ética** | Intento de despacho | Solicitud de publicación de un post en estado `draft` sin visto bueno. | Consola de administración o cliente REST. | Endpoint `/deliver` del Orquestador. | Bloqueo determinista de entrega retornando código de conflicto. | Retorno estricto de **HTTP 409** (ADR-008). |
| **QA-06** | **Aislamiento Multi-Tenant** | Operador multi-cuenta | Consulta RAG de lineamientos de marca desde un contexto cruzado. | Carga de trabajo concurrente. | Microservicio RAG y PostgreSQL. | Filtrado estricto por `brand_id` en el espacio vectorial. | Cero vectores de marcas competidoras devueltos. |

---

## 3. Conclusión de la Evaluación ATAM

Todos los escenarios de calidad formulados fueron validados satisfactoriamente durante las pruebas automatizadas del Capítulo 5, certificando que los compromisos de disponibilidad, seguridad y resiliencia se cumplen plenamente en la arquitectura contenerizada.
