# ANEXO 14. ESPECIFICACIÓN DE INTERFACES EXTERNAS (APIs)

<br>

<div align="center">

### TRABAJO DE GRADO — PRODUCTO TÉCNICO FORMAL
**PRUEBA DE CONCEPTO DE UN SISTEMA MULTIAGENTE BASADO EN MICROSERVICIOS Y CONTENEDORES PARA LA AUTOMATIZACIÓN DE LA PLANIFICACIÓN Y LA PUBLICACIÓN DE CONTENIDO EN LA EMPRESA ITY SAS**

<br>

**Autor:** Alvaro Felipe Lopez Russi &bull; Código: 67000867 &bull; \`aflopez67@ucatolica.edu.co\`  
**Universidad Católica de Colombia &bull; Facultad de Ingeniería**  
Programa de Ingeniería de Sistemas y Computación &bull; Bogotá D.C., 2026

</div>

---

## CONTROL DOCUMENTAL Y METADATOS DEL ANEXO

| Atributo | Detalle del Documento Técnico |
|---|---|
| **Identificador del Documento** | `ITY-MAS-ANX-014` (Anexo 14: Catálogo y Especificación de Interfaces Externas) |
| **Vinculación con Objetivos** | Cumplimiento formal de **OE2 (Requisitos de Interfaces Externas - Sección 5.4 SRS)** y **OE3 (Vistas de Integración de Arquitectura)** |
| **Estándar de Especificación** | **OpenAPI Specification (OAS) 3.0.3**, **IEEE Std 830-1998** e **ISO/IEC/IEEE 42010:2022** |
| **Entorno de Despliegue** | Docker Engine 26+, Docker Compose v2, FastAPI 0.110+, Python 3.11 |
| **Artefactos Digitales Adjuntos** | Archivo comprimido `Anexo_14_Interfaces.zip` con 10 contratos OpenAPI YAML y Colección Postman v2.1 |
| **Estado de Aprobación** | Revisado y Validado Técnicamente para la Prueba de Concepto |

---

## TABLA DE CONTENIDO DEL ANEXO 14

1. **Introducción y Propósito del Catálogo de Interfaces**
2. **Catálogo y Fichas Técnicas Resumidas de las 10 Interfaces (Físico)**
   - 2.1. IE-01: API de TikTok Research (Extracción de Tendencias e Insumos Virales)
   - 2.2. IE-02: API de Instagram Graph (Métricas de Audiencia y Publicación de Contenidos)
   - 2.3. IE-03: API de Procesamiento de Video (Motor FFmpeg / OpenCV)
   - 2.4. IE-04: API de Pasarela de Modelos de Lenguaje (LLM Gateway: Ollama / OpenAI / Groq)
   - 2.5. IE-05: API de Metricool REST (Planificador Multicanal Secundario / Fallback)
   - 2.6. IE-06: API de Gestión de Secretos (HashiCorp Vault Secrets Engine)
   - 2.7. IE-07: API de Notificaciones Operativas (WhatsApp Business Cloud API / Slack Webhooks)
   - 2.8. IE-08: API de YouTube Data v3 (Gestión de Video Horizontal y Shorts)
   - 2.9. IE-09: Sistema de Monitoreo y Telemetría (Prometheus Metrics / Grafana)
   - 2.10. IE-10: Sistema de Almacenamiento de Objetos S3 (MinIO / AWS S3 Compatible)
3. **Especificación y Justificación Exhaustiva de Postiz en la Arquitectura**
   - 3.1. Justificación Técnica: ¿Por qué Postiz frente a la Integración Directa con Meta Suite?
   - 3.2. Arquitectura de Desacoplamiento y Gestión Multi-Tenant en Docker
   - 3.3. Interacción de Postiz con el **Agente de Ideación y Estrategia (Ideator)**
   - 3.4. Interacción de Postiz con el **Agente de Publicación y Scheduling (Publisher)**
   - 3.5. Microservicio Interno `tool-postiz`: Contratos, Validación de Marca y Manejo de Errores
4. **Matriz de Trazabilidad Cruzada: Interfaces vs Requisitos IEEE 830 vs Cuellos de Botella ToC**
5. **Políticas de Seguridad, Cifrado y Cumplimiento de la Ley 1581 de 2012**
6. **Guía de Pruebas y Uso de la Colección de Postman Adjunta**

---

## 1. INTRODUCCIÓN Y PROPÓSITO DEL CATÁLOGO DE INTERFACES

En la ingeniería de sistemas distribuidos y arquitecturas de microservicios orientadas a agentes (AOMS - *Agent-Oriented MicroServices*), las **interfaces de comunicación externa (APIs)** constituyen las fronteras formales a través de las cuales los agentes de software perciben el entorno y ejecutan acciones sobre el mundo digital (Sycara, 2002; Collier et al., 2019). 

El presente anexo formaliza el catálogo completo de las diez interfaces externas que interactúan con el Sistema Multiagente (MAS) desarrollado para la agencia **ITY SAS**. Este catálogo cumple un triple propósito:
1. **Documentar formalmente los contratos técnicos (Swagger/OpenAPI 3.0)** de las herramientas externas utilizadas o potencialmente utilizables por el sistema.
2. **Garantizar el desacoplamiento arquitectónico**, asegurando que los agentes inteligentes no codifiquen URLs fijas ni credenciales maestras en su lógica interna, sino que invoquen operaciones a través de microservicios de herramientas (*tool services*) y gestores de secretos.
3. **Justificar con rigor de ingeniería la inclusión de la plataforma de código abierto Postiz** como el nodo integrador de publicación multicanal, detallando su interacción sinérgica tanto con el Agente de Ideación como con el Agente de Publicación.

---

## 2. CATÁLOGO Y FICHAS TÉCNICAS RESUMIDAS DE LAS 10 INTERFACES (FÍSICO)

A continuación se presentan las fichas técnicas normalizadas de las diez interfaces del sistema, especificando proveedor, rol funcional, mecanismos de autenticación, endpoints críticos, SLA de latencia y políticas de resiliencia.

```
========================================================================================================
                                     CATÁLOGO GENERAL DE LAS 10 INTERFACES
========================================================================================================
 [IE-01] TikTok Research API   --> [Agente Ideación]     : Minería de audios, retos y tendencias virales
 [IE-02] Instagram Graph API   --> [Agente Ideación]     : Métricas de engagement y perfil histórico
 [IE-03] Motor FFmpeg/OpenCV   --> [Agente Edición/QC]   : Validación técnica determinista de video (.mp4)
 [IE-04] LLM Gateway API       --> [Ambos Agentes]       : Inferencia, extracción semántica y copys
 [IE-05] Metricool REST API    --> [Agente Publicación]  : Planificador secundario de respaldo (Fallback)
 [IE-06] HashiCorp Vault API   --> [Sistema / Seguridad] : Custodia y rotación de credenciales AES-256
 [IE-07] WhatsApp / Slack API  --> [Sistema / Notific.]  : Alertas al equipo humano (Human-in-the-Loop)
 [IE-08] YouTube Data API v3   --> [Agente Publicación]  : Despliegue de contenidos 16:9 y Shorts
 [IE-09] Prometheus Exporter   --> [Observabilidad]      : Métricas de latencia, fallos y consumo RAM/CPU
 [IE-10] MinIO S3 Storage API  --> [Gestión Multimedia]  : Almacenamiento distribuido de renders y proxies
========================================================================================================
```

---

### 2.1. Ficha Técnica IE-01: API de TikTok Research

| Parámetro Técnico | Especificación de la Interfaz |
|---|---|
| **Identificador / Nombre** | `IE-01` &bull; **TikTok Research API v2** |
| **Proveedor Oficial** | ByteDance Ltd. / TikTok for Developers |
| **Agente Asociado** | **Agente 1: Ideación y Estrategia** (REQ-F01, REQ-F02) |
| **Rol en el Proceso** | Extracción automatizada de los 20 audios en tendencia, 10 retos virales y formatos de edición populares en Colombia. Mitiga el cuello de botella de búsqueda manual en feeds ($R_2$). |
| **Protocolo de Transporte** | HTTPS / REST &bull; Codificación: JSON UTF-8 |
| **Protocolo de Autenticación** | **OAuth 2.0 (Client Credentials Flow)** con rotación de tokens Bearer cada 2 horas. |
| **Endpoint Principal 1** | `POST https://open.tiktokapis.com/v2/research/video/query/` |
| **Payload de Entrada (Req)** | `{"query": {"and": [{"operation": "IN", "field_name": "hashtag_name", "field_values": ["skincarecolombia"]}, {"operation": "EQ", "field_name": "region_code", "field_values": ["CO"]}]}, "start_date": "20260801", "end_date": "20260828", "max_count": 20}` |
| **Respuesta Exitosa (200 OK)**| `{"data": {"videos": [{"id": "726190283", "view_count": 450200, "like_count": 32100, "music_id": "mus_88219"}]}, "error": {"code": "ok"}}` |
| **Latencia / SLA Esperado** | Percentil 95: $t \le 1.200$ ms |
| **Patrón de Resiliencia** | **Circuit Breaker** (umbral de 3 fallos consecutivos abre circuito hacia fallback de datos locales cacheados en Redis durante 24h - NFR-07). |

---

### 2.2. Ficha Técnica IE-02: API de Instagram Graph (Meta)

| Parámetro Técnico | Especificación de la Interfaz |
|---|---|
| **Identificador / Nombre** | `IE-02` &bull; **Instagram Graph API (Meta Business Suite v21.0)** |
| **Proveedor Oficial** | Meta Platforms Inc. |
| **Agente Asociado** | **Agente 1: Ideación** (REQ-F04, REQ-F05) y **Agente 3: Publicación** (REQ-F21) |
| **Rol en el Proceso** | Consulta de métricas históricas de rendimiento de cuenta (alcance, engagement, impresiones) y verificación de estado de cuenta comercial. |
| **Protocolo de Transporte** | HTTPS / REST &bull; Formato: JSON |
| **Protocolo de Autenticación** | **User Access Token de Larga Duración (60 días)** con permisos `instagram_basic`, `instagram_manage_insights`, `pages_read_engagement`. |
| **Endpoint Principal 1** | `GET https://graph.facebook.com/v21.0/{ig-user-id}/insights?metric=reach,impressions,profile_views&period=day` |
| **Endpoint Principal 2** | `POST https://graph.facebook.com/v21.0/{ig-user-id}/media_publish?creation_id={creation-id}` |
| **Respuesta Exitosa (200 OK)**| `{"data": [{"name": "reach", "period": "day", "values": [{"value": 14200, "end_time": "2026-08-28T07:00:00+0000"}]}]}` |
| **Manejo de Errores** | Mapeo de errores de token caducado (`OAuthException`, subcódigo 463/467) con alerta directa al líder de proyecto vía IE-07. |

---

### 2.3. Ficha Técnica IE-03: Motor de Procesamiento Multimedia FFmpeg / OpenCV

| Parámetro Técnico | Especificación de la Interfaz |
|---|---|
| **Identificador / Nombre** | `IE-03` &bull; **Motor Local de Inspección de Video (FFmpeg 6.1 / OpenCV 4.9)** |
| **Proveedor Oficial** | Proyecto de Software Libre FFmpeg / OpenCV Foundation |
| **Agente Asociado** | **Agente 2: Control de Calidad y Edición Asistida** (REQ-F11, REQ-F13, REQ-F15, REQ-F18) |
| **Rol en el Proceso** | Validación técnica determinista del video renderizado: verificación de relación de aspecto 9:16 ($1080 	imes 1920$), duración máxima (90s reels, 60s historias), volumen sonoro ($-16$ a $-12$ LUFS según norma ITU-R BS.1770) y presencia de logotipo en los primeros 3 segundos. Ataca directamente la Restricción Crítica $R_1$. |
| **Protocolo de Transporte** | Ejecución local en contenedor Docker / Subprocess CLI & Binding C++/Python (`ffmpeg-python`, `cv2`) |
| **Protocolo de Autenticación** | Aislamiento de contenedor Docker local (sin dependencias de red externa). |
| **Comando / Endpoint Clave** | `ffprobe -v error -select_streams v:0 -show_entries stream=width,height,duration,r_frame_rate -of json {input_file.mp4}` |
| **Comando Análisis Audio** | `ffmpeg -i {input_file.mp4} -af ebur128=framelog=verbose -f null -` |
| **Respuesta Estructurada** | `{"width": 1080, "height": 1920, "duration": 45.2, "integrated_lufs": -14.2, "aspect_ratio": "9:16", "qc_passed": true}` |
| **Latencia / SLA** | Validación completa de video de 60 segundos en $t \le 15$ segundos. |

---

### 2.4. Ficha Técnica IE-04: API de Pasarela de Modelos de Lenguaje (LLM Gateway)

| Parámetro Técnico | Especificación de la Interfaz |
|---|---|
| **Identificador / Nombre** | `IE-04` &bull; **LLM Gateway Service (Microservicio Interno :8003)** |
| **Proveedor Oficial** | Desarrollo propio de ITY SAS con soporte multiproveedor (Ollama local, OpenAI API, Groq Cloud) |
| **Agente Asociado** | **Ambos Agentes:** Agente de Ideación (REQ-F02, REQ-F06) y Agente de Publicación (REQ-F22, REQ-F28) |
| **Rol en el Proceso** | Inferencia cognitiva unificada: estructuración de briefs a esquemas Pydantic, extracción de 5 palabras clave, análisis de tono de marca y generación de 3 variantes de copy multicanal. |
| **Protocolo de Transporte** | HTTP/1.1 REST &bull; Formato: JSON UTF-8 |
| **Protocolo de Autenticación** | Bearer Token interno en cabecera `Authorization` & API Keys upstream cifradas en Vault. |
| **Endpoint Principal 1** | `POST http://llm-gateway:8003/v1/generate` (Generación de texto y JSON Schema estructurado) |
| **Endpoint Principal 2** | `POST http://llm-gateway:8003/v1/embeddings` (Generación de vectores para búsqueda semántica RAG) |
| **Payload de Ejemplo** | `{"prompt": "Escribe copy para Instagram...", "system": "Voz de marca Amatu...", "model": "llama3:8b", "temperature": 0.7, "json_schema": {...}}` |
| **Respuesta Exitosa** | `{"content": "...", "provider": "ollama", "model": "llama3:8b", "cached": false, "duration_ms": 1420}` |
| **Políticas de Resiliencia** | Caché en Redis (TTL 1 hora para generación, 24 horas para embeddings), reintentos automáticos con backoff exponencial y degradación elegante a modelo SLM local en caso de caída cloud. |

---

### 2.5. Ficha Técnica IE-05: API REST de Metricool (Scheduling Secundario)

| Parámetro Técnico | Especificación de la Interfaz |
|---|---|
| **Identificador / Nombre** | `IE-05` &bull; **Metricool Planner REST API v1** |
| **Proveedor Oficial** | D rigid Technologies S.L. / Metricool |
| **Agente Asociado** | **Agente 3: Publicación y Scheduling** (REQ-F23, REQ-F30) |
| **Rol en el Proceso** | Servicio alternativo de programación de respaldo (Fallback) en caso de indisponibilidad temporal del servidor Postiz. |
| **Protocolo de Transporte** | HTTPS / REST &bull; JSON |
| **Protocolo de Autenticación** | Cabecera personalizada de seguridad `X-MC-TOKEN` con clave API comercial. |
| **Endpoint Principal** | `POST https://app.metricool.com/api/v1/planner/posts` |
| **Payload de Entrada** | `{"text": "Copy validado", "publicationDate": "2026-08-25T18:00:00Z", "networks": ["INSTAGRAM", "TIKTOK"]}` |
| **Respuesta Exitosa** | `{"status": "scheduled", "id": "mc_post_9921", "scheduledDate": "2026-08-25T18:00:00Z"}` |

---

### 2.6. Ficha Técnica IE-06: API de Gestión de Secretos (HashiCorp Vault)

| Parámetro Técnico | Especificación de la Interfaz |
|---|---|
| **Identificador / Nombre** | `IE-06` &bull; **HashiCorp Vault Key-Value Secrets Engine v2** |
| **Proveedor Oficial** | HashiCorp Inc. |
| **Agente Asociado** | **Infraestructura Transversal del Sistema** (NFR-04, NFR-09) |
| **Rol en el Proceso** | Custodia de credenciales sensibles, tokens OAuth y API Keys. Ningún agente almacena claves en texto plano. Soporta rotación automática programada cada 90 días. |
| **Protocolo de Transporte** | HTTPS / REST &bull; Formato: JSON |
| **Protocolo de Autenticación** | **Token de Servicio (`X-Vault-Token`)** o AppRole con privilegios mínimos de lectura según el ID de la marca. |
| **Endpoint Principal** | `GET http://vault:8200/v1/secret/data/brands/{brand_id}/{service_name}` |
| **Respuesta Exitosa** | `{"data": {"data": {"api_key": "postiz_sec_...", "token": "EAAB..."}}, "lease_duration": 7776000}` |
| **Cifrado en Reposo** | **AES-256-GCM** en el backend de persistencia. |

---

### 2.7. Ficha Técnica IE-07: API de Notificaciones (WhatsApp Business Cloud / Slack)

| Parámetro Técnico | Especificación de la Interfaz |
|---|---|
| **Identificador / Nombre** | `IE-07` &bull; **WhatsApp Business Cloud API (Meta) & Slack Incoming Webhooks** |
| **Proveedor Oficial** | Meta Platforms Inc. / Slack Technologies |
| **Agente Asociado** | **Agente 2: Edición** (REQ-F19) y **Agente 3: Publicación** (REQ-F30) |
| **Rol en el Proceso** | Canal formal de alertamiento en el paradigma Human-in-the-Loop (HITL). Notifica al Director Creativo ante rechazos en el control de calidad y alerta al Community Manager cuando un post queda programado exitosamente. |
| **Protocolo de Transporte** | HTTPS / REST &bull; JSON |
| **Protocolo de Autenticación** | Bearer Token OAuth 2.0 (WhatsApp) y Webhook Token URL (Slack). |
| **Endpoint Principal** | `POST https://graph.facebook.com/v21.0/{phone-id}/messages` |
| **Payload de Entrada** | `{"messaging_product": "whatsapp", "to": "573105551234", "type": "text", "text": {"body": "Alerta MAS: Reel 2026-08_001 aprobado técnicamente."}}` |
| **SLA de Notificación** | Despacho de alerta en $t \le 2$ segundos desde el evento en RabbitMQ. |

---

### 2.8. Ficha Técnica IE-08: API de YouTube Data v3

| Parámetro Técnico | Especificación de la Interfaz |
|---|---|
| **Identificador / Nombre** | `IE-08` &bull; **Google YouTube Data API v3** |
| **Proveedor Oficial** | Google LLC / Alphabet Inc. |
| **Agente Asociado** | **Agente 3: Publicación y Scheduling** (REQ-F21, REQ-F23) |
| **Rol en el Proceso** | Publicación de videos de formato horizontal (16:9) y verticales (YouTube Shorts), gestión de títulos, etiquetas SEO y extracción de métricas de visualización. |
| **Protocolo de Transporte** | HTTPS / REST Multipart Upload &bull; JSON |
| **Protocolo de Autenticación** | **OAuth 2.0 (Google Identity)** con alcance `https://www.googleapis.com/auth/youtube.upload`. |
| **Endpoint Principal** | `POST https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status` |
| **Respuesta Exitosa** | `{"id": "yt_vid_9921", "snippet": {"title": "Campaña Verano"}, "status": {"privacyStatus": "public"}}` |

---

### 2.9. Ficha Técnica IE-09: Sistema de Monitoreo y Telemetría (Prometheus)

| Parámetro Técnico | Especificación de la Interfaz |
|---|---|
| **Identificador / Nombre** | `IE-09` &bull; **Prometheus Metrics Exporter API** |
| **Proveedor Oficial** | Cloud Native Computing Foundation (CNCF) |
| **Agente Asociado** | **Monitoreo Global del Ecosistema Multiagente** (NFR-03, NFR-05) |
| **Rol en el Proceso** | Exportación de métricas de salud en tiempo real: tasa de éxito de tareas, latencia p50/p95 por agente, uso de memoria/CPU en contenedores Docker y número de mensajes en cola RabbitMQ. |
| **Protocolo de Transporte** | HTTP / Text Metrics Format &bull; Scraping cíclico cada 15 segundos |
| **Endpoint Principal** | `GET http://{service-host}:{port}/metrics` |
| **Métricas Clave Exportadas** | `agent_tasks_total`, `agent_execution_duration_seconds_bucket`, `rabbitmq_queue_messages`, `llm_gateway_token_usage_total` |
| **Visualización** | Cuadros de mando interactivos en **Grafana Dashboards**. |

---

### 2.10. Ficha Técnica IE-10: Sistema de Almacenamiento de Objetos S3 (MinIO)

| Parámetro Técnico | Especificación de la Interfaz |
|---|---|
| **Identificador / Nombre** | `IE-10` &bull; **MinIO S3-Compatible Distributed Object Storage** |
| **Proveedor Oficial** | MinIO Inc. / Protocolo Amazon S3 API |
| **Agente Asociado** | **Agente 2: Edición** (REQ-F17) y **Agente 3: Publicación** (REQ-F27) |
| **Rol en el Proceso** | Repositorio centralizado de activos digitales: almacenamiento de archivos de video crudo (.mp4), miniaturas de portada (*thumbnails*), archivos proxy de baja resolución para revisión rápida y bitácoras estructuradas de simulación. |
| **Protocolo de Transporte** | HTTP/HTTPS &bull; AWS Signature Version 4 (HMAC-SHA256) |
| **Endpoint Principal 1** | `PUT http://minio:9000/{bucket}/{object_name}` (Carga de archivo multimedia) |
| **Endpoint Principal 2** | `GET http://minio:9000/{bucket}/{object_name}?presigned=true` (Generación de URL temporal segura de descarga para el cliente) |
| **Estructura de Buckets** | `ity-media/raw/`, `ity-media/renders/`, `ity-media/proxies/`, `ity-media/thumbnails/` |

---

## 3. ESPECIFICACIÓN Y JUSTIFICACIÓN EXHAUSTIVA DE POSTIZ EN LA ARQUITECTURA

```
+---------------------------------------------------------------------------------------------------------+
|                                    ARQUITECTURA DE INTEGRACIÓN CON POSTIZ                               |
+---------------------------------------------------------------------------------------------------------+
|                                                                                                         |
|   +--------------------------+                         +--------------------------+                     |
|   |   AGENTE 1: IDEACIÓN     |                         |  AGENTE 2: PUBLICACIÓN   |                     |
|   |   (Rol: Ideator)         |                         |  (Rol: Publisher)        |                     |
|   +------------+-------------+                         +------------+-------------+                     |
|                |                                                    |                                   |
|                | 1. Consulta canales activos                        | 3. Despacho de variantes de copy  |
|                |    y formatos soportados                           |    y programación con timestamp   |
|                v                                                    v                                   |
|   +-------------------------------------------------------------------------------+                     |
|   |         MICROSERVICIO INTERNO TOOL-POSTIZ (FastAPI :8016 / AMQP)             |                     |
|   |         • Manifiesto estandarizado /.well-known/tool-manifest                 |                     |
|   |         • Validación de aislamiento multi-tenant contra PostgreSQL            |                     |
|   |         • Mapeo estricto de brand_id contra tabla brand_channels             |                     |
|   +---------------------------------------+---------------------------------------+                     |
|                                           |                                                             |
|                                           | Invocación HTTP segura (POSTIZ_API_KEY)                     |
|                                           v                                                             |
|   +-------------------------------------------------------------------------------+                     |
|   |                  SERVIDOR POSTIZ (Open-Source / Docker Compose)               |                     |
|   |         • Pasarela de conexión oficial hacia APIs de redes sociales           |                     |
|   |         • Gestión interna de OAuth, refresco de tokens y webhooks             |                     |
|   +---+-------------------+-------------------+-------------------+---------------+                     |
|       |                   |                   |                   |                                     |
|       v                   v                   v                   v                                     |
|   [Instagram API]     [TikTok API]      [LinkedIn API]      [YouTube API]                               |
|                                                                                                         |
+---------------------------------------------------------------------------------------------------------+
```

### 3.1. Justificación Técnica: ¿Por qué Postiz frente a la Integración Directa con Meta Suite?

Uno de los principales aportes de ingeniería del presente proyecto de grado consiste en la selección y despliegue de **Postiz** como la plataforma unificada de publicación social. Durante la fase de diagnóstico (Capítulo 2 y 3), se evaluó inicialmente la posibilidad de conectar los agentes directamente contra la API oficial de Meta Graph (Meta Business Suite). Sin embargo, un análisis arquitectónico riguroso demostró que la integración directa con Meta presentaba cinco barreras insalvables para una agencia como ITY SAS:

1. **La Barrera de la Verificación Empresarial de Meta (Meta Business Verification):** El acceso en modo de producción a los permisos de publicación de Meta (`instagram_content_publish`, `pages_manage_posts`) exige que la empresa supere una auditoría corporativa formal ante Meta en Estados Unidos, con presentación de registros tributarios (RUT), escrituras públicas y certificados bancarios notariados. Este trámite suele demorar entre 8 y 16 semanas, y ante cualquier cambio de razón social bloquea intempestivamente el acceso a las APIs, paralizando la entrega de las campañas de los clientes.
2. **La Caducidad Forzosa de Tokens OAuth (El Síndrome de la Sesión Invalida):** Los tokens de usuario de Meta expiran forzosamente a los 60 días, y se invalidan de manera inmediata si el cliente cambia la contraseña de su cuenta personal de Facebook o activa la autenticación de dos factores. En el flujo manual As-Is, documentamos que esto genera la **Desviación Crítica UP-5 (Caducidad de Tokens)**, deteniendo la publicación durante horas. Postiz resuelve esto al contar con un demonio interno de refresco automático de tokens (*background token refresh daemon*) que renueva las sesiones de forma transparente.
3. **Dispersión de Endpoints Heterogéneos:** Si el sistema multiagente se conectara directamente a las redes sociales, el Agente de Publicación debería implementar seis librerías SDK completamente diferentes: una para Meta Graph API, otra para TikTok Open API, otra para LinkedIn Marketing Developer Platform y otra para Google YouTube API. Esto multiplicaría exponencialmente el código de integración, el acoplamiento y los puntos potenciales de falla.
4. **Postiz es Open-Source y Auto-Hospedable (Docker):** Postiz es una solución de código abierto de última generación, completamente gobernable y desplegable mediante Docker Compose (incluida directamente en el repositorio del proyecto en `postiz/postiz-docker-compose`). Esto otorga a ITY SAS una ventaja decisiva: **cero dependencia de proveedores externos de pago (sin costos por usuario o suscripciones de \$99/mes)** y soberanía total sobre los datos.
5. **Cumplimiento Estricto con la Ley 1581 de 2012 (Protección de Datos):** Al ejecutarse localmente en la infraestructura de la agencia, las contraseñas, tokens y borradores de contenido confidencial de los clientes no viajan a través de servidores de terceros no certificados, garantizando que el tratamiento de datos permanezca bajo estricta jurisdicción nacional.

---

### 3.2. Arquitectura de Desacoplamiento y Gestión Multi-Tenant en Docker

El sistema multiagente no se conecta a Postiz de forma caótica. La arquitectura impone una **capa de desacoplamiento e intermediación** mediante el microservicio interno `tool-postiz` (puerto `:8016`), el cual garantiza el aislamiento multi-tenant a través de la tabla `brand_channels` en PostgreSQL:

```sql
CREATE TABLE brand_channels (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    provider VARCHAR(64) NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    status VARCHAR(32) DEFAULT 'active',
    settings JSONB DEFAULT '{}'::jsonb,
    credential_reference VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_brand_channels_provider_external UNIQUE (provider, external_id)
);
```

Cuando un agente solicita una acción de publicación, `tool-postiz` intercepta la petición y verifica en PostgreSQL que los `integration_ids` enviados correspondan efectivamente a la marca del brief (`brand_id`). Si un usuario o agente intenta enviar contenido a un canal perteneciente a otra marca, la pasarela aborta la operación con un error de seguridad, garantizando que **jamás ocurra una fuga de información o publicación cruzada entre marcas competidoras**.

---

### 3.3. Interacción de Postiz con el Agente de Ideación y Estrategia (Ideator)

Existe un error conceptual común en la industria al asumir que las herramientas de publicación solo deben ser utilizadas al final del flujo por el publicador. En el Sistema Multiagente de ITY SAS, **el Agente de Ideación interactúa intensamente con Postiz en el front-end del proceso**, cumpliendo tres funciones estratégicas:

1. **Descubrimiento Preventivo de Canales Activos:**
   Antes de generar el concepto creativo o escribir el guion técnico, el Agente de Ideación invoca la operación `op_integrations()` de `tool-postiz`. Si la consulta revela que la marca *Amatu* solo tiene activos canales de Instagram y TikTok (pero no tiene LinkedIn vinculado), el agente descarta de inmediato la sugerencia de formatos B2B o artículos densos, orientando su razonamiento exclusivamente a piezas verticales de alto impacto visual.
2. **Ingesta de Restricciones Técnicas por Plataforma:**
   Cada canal social conectado en Postiz reporta metadatos sobre sus límites técnicos vigentes (ej. duración máxima admitida, resolución recomendada y límites de caracteres en la descripción). El Agente de Ideación ingesta estas restricciones y las inyecta en el prompt del LLM Gateway, garantizando que el brief formulado cumpla desde el segundo cero con los parámetros técnicos de los destinos finales de la marca.
3. **Retroalimentación de Patrones de Éxito:**
   A través del endpoint de historial de publicaciones de Postiz, el Agente de Ideación puede auditar qué publicaciones pasadas de la cuenta lograron mejor tracción y cuáles sufrieron errores de entrega, evitando repetir temáticas agotadas y combatiendo la **fatiga publicitaria (35-40 días)** documentada en el diagnóstico operativo.

---

### 3.4. Interacción de Postiz con el Agente de Publicación y Scheduling (Publisher)

Para el **Agente de Publicación**, Postiz actúa como su brazo ejecutor directo en el mundo exterior, materializando las siguientes tareas críticas:

1. **Gestión de Variantes de Copy Multicanal:**
   El agente no publica un texto genérico idéntico en todas las redes. Utiliza el parámetro `contents` del contrato de Postiz:
   ```json
   {
     "content": "Texto base universal...",
     "contents": {
       "instagram": "Copy visual con emojis y llamado a la acción al enlace en bio...",
       "tiktok": "Gancho conversacional rápido y hashtags en tendencia...",
       "linkedin": "Enfoque corporativo, reflexivo y datos de la industria..."
     }
   }
   ```
2. **Programación Temporal con Zona Horaria Exacta:**
   El agente calcula la hora óptima de publicación basándose en el historial de engagement de la cuenta y remite el timestamp formal en formato UTC (`publish_at: "2026-08-25T18:00:00Z"`). Postiz toma la custodia del post y lo mantiene encolado hasta el milisegundo exacto programado.
3. **Control del Modo de Publicación:**
   El agente soporta tres modalidades de trabajo según las directrices del cliente:
   - `mode: "draft"`: Crea el contenido como borrador en Postiz para que el Community Manager humano lo revise antes de autorizarlo (modo recomendado para clientes nuevos).
   - `mode: "schedule"`: Programa la publicación para su difusión autónoma en la fecha establecida.
   - `mode: "immediate"`: Ejecuta la publicación instantánea para noticias de última hora o eventos en vivo.
4. **Tolerancia a Fallos y Reintentos:**
   Si la API de una red social presenta un microcorte transitorio, Postiz implementa reintentos automáticos internos y notifica al agente el estado resultante (`published` o `error`), permitiendo registrar el evento en la auditoría sin requerir intervención humana de urgencia.

---

### 3.5. Microservicio Interno `tool-postiz`: Contratos y Manejo de Errores

El microservicio `tool-postiz` expone una interfaz limpia sobre FastAPI y un servidor RPC sobre AMQP (RabbitMQ). La siguiente tabla documenta los contratos principales de este servicio:

| Método / Ruta | Entrada Principal | Salida Estructurada | Comportamiento Técnico |
|---|---|---|---|
| `GET /.well-known/tool-manifest` | Vacío | `{"name": "postiz", "version": "1.0.0", "operations": [...]}` | Expone el manifiesto para descubrimiento dinámico en el `ToolRegistry`. |
| `GET /integrations` | `group` (opcional) | `{"status": "ok", "data": [{"id": "...", "provider": "..."}]}` | Retorna los canales conectados. Si `POSTIZ_API_KEY` no está configurada, devuelve envelope con `status: "error"` sin tumbar el servicio. |
| `POST /posts` | Objeto `CreatePostBody` | `{"status": "ok", "data": {"post_id": "...", "mode": "schedule"}}` | Valida permisos en PostgreSQL, arma el payload JSON y llama a `/public/v1/posts` de Postiz. |
| `POST /link_channel` | Objeto `LinkChannelBody` | `{"status": "ok", "data": {"linked": true}}` | Asocia un `external_id` de Postiz a un `brand_id` en la tabla `brand_channels`. |

---

## 4. MATRIZ DE TRAZABILIDAD CRUZADA: INTERFACES VS REQUISITOS VS TOC

La Tabla 4.1 demuestra la exhaustiva coherencia ingenieril del proyecto, cruzando cada interfaz externa con los requisitos funcionales del estándar IEEE Std 830-1998 (Fase 2) y los cuellos de botella priorizados mediante la Teoría de Restricciones (Fase 1 / OE1).

#### Tabla 4.1: Matriz de Trazabilidad Integral: Interfaces Externas vs Requisitos IEEE 830 vs Cuellos de Botella ToC.
| ID Interfaz | Nombre de la Interfaz | Agente Responsable | Requisitos Funcionales IEEE 830 | Requisitos No Funcionales | Cuello de Botella ToC Mitigado | Nivel de Cobertura |
|:---:|---|---|---|---|:---:|:---:|
| **IE-01** | TikTok Research API | Agente de Ideación | REQ-F01, REQ-F02 | REQ-NF02, REQ-NF07 | **$R_2$** (Ideación, $IC=14/15$) | Completa (100%) |
| **IE-02** | Instagram Graph API | Agente de Ideación y Publ. | REQ-F04, REQ-F05 | REQ-NF02, REQ-NF04 | **$R_2$** y **$R_3$** | Completa (100%) |
| **IE-03** | Motor FFmpeg / OpenCV | Agente de Edición / QC | REQ-F11, REQ-F13, REQ-F15, REQ-F18 | REQ-NF01, REQ-NF08 | **$R_1$** (Edición Video, $IC=15/15$) | Completa (100%) |
| **IE-04** | LLM Gateway Service | Ambos Agentes | REQ-F02, REQ-F06, REQ-F22, REQ-F28 | REQ-NF02, REQ-NF07 | **$R_1$, $R_2$ y $R_3$** | Transversal |
| **IE-05** | Metricool REST API | Agente de Publicación | REQ-F23, REQ-F30 | REQ-NF02, REQ-NF07 | **$R_3$** (Publicación, $IC=12/15$) | Respaldo (Fallback) |
| **IE-06** | HashiCorp Vault API | Infraestructura Transversal | REQ-F30 | REQ-NF04, REQ-NF09 | Transversal (Seguridad) | Completa (100%) |
| **IE-07** | WhatsApp / Slack API | Agente de Edición y Publ. | REQ-F19, REQ-F30 | REQ-NF06, REQ-NF09 | **$R_1$** y **$R_4$** (Alertas HITL) | Completa (100%) |
| **IE-08** | YouTube Data API v3 | Agente de Publicación | REQ-F21, REQ-F23 | REQ-NF02, REQ-NF04 | **$R_3$** (Formatos 16:9 y Shorts) | Completa (100%) |
| **IE-09** | Prometheus Metrics | Infraestructura Transversal | Diagnóstico y SLOs | REQ-NF03, REQ-NF05 | Monitoreo de Capacidad | Completa (100%) |
| **IE-10** | MinIO S3 Object Storage | Agente de Edición y Publ. | REQ-F17, REQ-F27 | REQ-NF01, REQ-NF05 | **$R_1$** y **$R_3$** (Almacenamiento) | Completa (100%) |

---

## 5. POLÍTICAS DE SEGURIDAD, CIFRADO Y LEY 1581 DE 2012

El manejo de interfaces externas en un entorno de agencia publicitaria exige estrictos resguardos para proteger el secreto comercial de los clientes y la privacidad de las audiencias:

1. **Principio de Mínimo Privilegio (PoLP):** Cada microservicio y agente dispone exclusivamente de las credenciales indispensables para ejecutar su tarea asignada. El Agente de Ideación únicamente cuenta con permisos de lectura en analítica (`read-only`), careciendo de privilegios para ejecutar o alterar publicaciones.
2. **Cifrado en Tránsito y en Reposo:** Todas las comunicaciones hacia APIs públicas externas se realizan obligatoriamente bajo **TLS 1.3 (HTTPS)** con validación estricta de certificados CA. Las credenciales, tokens de larga duración y API Keys se almacenan cifradas en Vault bajo el algoritmo **AES-256-GCM** (NFR-04).
3. **Cumplimiento de la Ley 1581 de 2012 (Régimen de Protección de Datos Personales en Colombia):** En estricto acatamiento del REQ-NF09:
   - El sistema **no almacena nombres propios, números telefónicos, direcciones de correo ni identificadores biométricos de los usuarios finales** que interactúan con las redes sociales de las marcas.
   - Las consultas de analítica (IE-01, IE-02) recuperan exclusivamente datos macro agregados y anonimizados (alcance, volumen de impresiones, distribución por país).
   - Toda información corporativa sensible de los clientes se almacena bajo esquemas de aislamiento lógico multi-tenant con claves foráneas compuestas (`organization_id`, `brand_id`), imposibilitando la mezcla accidental de datos entre diferentes marcas comerciales.

---

## 6. GUÍA DE PRUEBAS Y USO DE LA COLECCIÓN DE POSTMAN ADJUNTA

Como parte del contenido digital complementario de este Anexo 14, se entrega la carpeta comprimida `Anexo_14_Interfaces.zip`, la cual contiene la colección ejecutable de Postman y su correspondiente entorno parametrizado:

### 6.1. Contenido del Paquete Digital `Anexo_14_Interfaces.zip`
- `openapi/`: Directorio con los 10 archivos de especificación formal en formato **OpenAPI 3.0.3 (YAML)** para cada una de las interfaces catalogadas.
- `postman/ITY_SAS_Interfaces_Externas.postman_collection.json`: Colección formal de Postman v2.1 organizada en cuatro carpetas de prueba:
  1. *01 - Agente de Ideación y Estrategia* (Peticiones a TikTok Research, Instagram Insights, LLM Gateway y consulta preventiva de canales Postiz).
  2. *02 - Agente de Publicación y Scheduling* (Generación de copys, programación en Postiz con variantes por red, fallback en Metricool y subida a YouTube).
  3. *03 - Servicios de Soporte, Seguridad y Almacenamiento* (Lectura de secretos en Vault, notificaciones WhatsApp, subida binaria a MinIO S3 y métricas Prometheus).
  4. *04 - Microservicio Interno Tool-Postiz (:8016)* (Llamadas a `/.well-known/tool-manifest`, `/posts` y `/link_channel`).
- `postman/ITY_SAS_Environment.postman_environment.json`: Entorno de variables parametrizadas (`postiz_api_url`, `postiz_api_key`, `llm_gateway_url`, `brand_id`, etc.).

### 6.2. Instrucciones de Importación y Ejecución en Postman
1. Abrir la aplicación **Postman** (versión 10+).
2. Hacer clic en el botón superior **Import** y seleccionar los dos archivos JSON ubicados en la carpeta `postman/`.
3. En la esquina superior derecha de Postman, seleccionar el entorno activo: **`ITY SAS Multiagent Environment`**.
4. Abrir la colección y ejecutar las pruebas de extremo a extremo utilizando el **Collection Runner** de Postman para certificar los códigos de retorno `200 OK` y la conformidad de los contratos JSON.

---

<div align="center">

### FIN DEL ANEXO 14 — ESPECIFICACIÓN DE INTERFACES EXTERNAS (APIs)
**Universidad Católica de Colombia &bull; Facultad de Ingeniería**  
*Bogotá D.C., Colombia — 2026*

</div>
