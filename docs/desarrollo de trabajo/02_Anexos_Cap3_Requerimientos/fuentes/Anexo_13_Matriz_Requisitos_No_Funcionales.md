# Anexo 13. Matriz Detallada de los 9 Requisitos No Funcionales (NFR)

<div class="meta">
<b>Capítulo:</b> 3 (Especificación de Requerimientos) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE2 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Introducción y Marco de Calidad de Software

Los Requisitos No Funcionales (NFR) definen las restricciones operativas, los atributos de calidad sistémica y los criterios de rendimiento que gobiernan la arquitectura del sistema multiagente. En conformidad con la norma **ISO/IEC 25010** y el estándar **IEEE Std 830-1998**, cada requerimiento no funcional se especificó con métricas objetivas, umbrales cuantitativos y mecanismos formales de verificación.

---

## 2. Catálogo Oficial de los 9 Requisitos No Funcionales

| Código | Dimensión de Calidad | Parámetro Evaluado | Especificación Técnica y Umbral de Aceptación | Prioridad MoSCoW | Mecanismo de Verificación |
|:---:|---|---|---|:---:|---|
| **REQ-NF01** | **Portabilidad** | Contenedorización y tamaño de imagen | Cada microservicio debe empaquetarse en contenedores Docker independientes basados en imágenes ligeras (`python:3.10-slim` o `alpine`). El tamaño de imagen no debe superar **500 MB** por servicio (excluyendo pesos de modelos LLM locales). | **Must** | Inspección automatizada mediante `docker images` en el pipeline CI/CD. |
| **REQ-NF02** | **Rendimiento** | Latencia entre microservicios | El percentil 95 ($P_{95}$) de latencia en invocaciones REST síncronas entre microservicios locales debe ser inferior a **500 ms**. La inferencia cognitiva de agentes en LLM Gateway debe responder en un $P_{95} < 5,0$ s en hardware host. | **Must** | Pruebas de carga automatizadas con Locust y suite `pytest -m performance`. |
| **REQ-NF03** | **Disponibilidad** | Tiempo de actividad de la plataforma | Disponibilidad del servicio del **99,5%** en horario de oficina (8:00 a 18:00 COT, lunes a viernes) y **99,0%** en horario no laboral, con tolerancia a fallos transitorios mediante colas persistentes. | **Must** | Sondas de monitoreo continuo (Healthchecks en Docker Compose cada 10 s). |
| **REQ-NF04** | **Seguridad** | Cifrado y gestión de secretos | Cifrado en reposo para credenciales de clientes mediante algoritmo **AES-256-GCM**. Gestión de secretos mediante variables de entorno desacopladas (`.env`), prohibiendo claves en duro en el repositorio Git. | **Must** | Análisis estático de seguridad con Bandit y escaneo de secretos con GitLeaks. |
| **REQ-NF05** | **Escalabilidad** | Capacidad de concurrencia | Arquitectura basada en microservicios *stateless* capaces de escalar horizontalmente a nivel de workers AMQP y réplicas de inferencia, soportando picos de al menos **10 solicitudes de briefs simultáneas** sin degradación de estado. | **Should** | Pruebas de estrés con 45 briefs concurrentes documentadas en el Escenario E2. |
| **REQ-NF06** | **Mantenibilidad** | Observabilidad y retención de logs | Centralización estructurada de logs en formato JSON con correlación por `trace_id`. Retención de bitácoras de auditoría de al menos **90 días**, exportables para revisión administrativa. | **Should** | Rotación automática de logs en contenedores y trazabilidad con LangSmith. |
| **REQ-NF07** | **Resiliencia** | Fallback ante indisponibilidad de LLM | El LLM Gateway debe implementar conmutación por error (*fallback*) automática multi-proveedor: si el modelo primario falla o supera 10 s de latencia, conmuta transparentemente al modelo secundario sin interrumpir el flujo. | **Must** | Pruebas unitarias de inyección de fallos en `test_llm_gateway.py` (29 tests aprobados). |
| **REQ-NF08** | **Eficiencia** | Tiempo de arranque (*Cold Start*) | Tiempo de levantamiento completo de la pila de contenedores (`docker compose up -d`) menor a **15 segundos** para servicios base y menor a **45 segundos** para la totalidad de los 14 microservicios. | **Should** | Medición cronometrada con `Measure-Command` en el entorno de despliegue. |
| **REQ-NF09** | **Cumplimiento Legal** | Protección de datos personales | Cumplimiento estricto de la **Ley Estatutaria 1581 de 2012** (Colombia). Aislamiento lógico multi-tenant por marca (`brand_id`), impidiendo la filtración cruzada de datos comerciales confidenciales. | **Must** | Validación de políticas RLS y pruebas multitenant en `test_rag_multitenant.py`. |

---

## 3. Conclusiones y Mapeo con Escenarios de Arquitectura

Los 9 requisitos no funcionales sirvieron de entrada directa para la formulación de los escenarios de calidad evaluados bajo la metodología **ATAM** (*Architecture Tradeoff Analysis Method*) en el Capítulo 4 (Anexo 24), garantizando que las decisiones de diseño (como el uso de RabbitMQ para resiliencia y PostgreSQL con `pgvector` para aislamiento) respondan a compromisos verificables.
