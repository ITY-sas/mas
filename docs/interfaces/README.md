# Anexo 14: Especificación de Interfaces Externas (APIs)

**Universidad Católica de Colombia &bull; Facultad de Ingeniería**  
**Programa de Ingeniería de Sistemas y Computación &bull; Trabajo de Grado 2026**  
**Autor:** Alvaro Felipe Lopez Russi (Código: 67000867) &bull; `aflopez67@ucatolica.edu.co`  
**Caso de Estudio:** ITY SAS  

---

## 1. Descripción del Entregable

El **Anexo 14. Especificación de Interfaces Externas (APIs)** es un producto formal de ingeniería de software que documenta de manera exhaustiva todos los contratos de comunicación, protocolos de autenticación, políticas de seguridad y modelos de resiliencia para las diez (10) interfaces que interactúan con el Sistema Multiagente (MAS) desarrollado para la agencia publicitaria **ITY SAS**.

Este anexo da cumplimiento estricto a:
* **Objetivo Específico 2 (OE2):** Sección 5.4 del Documento de Especificación de Requisitos de Software (SRS) según la norma **IEEE Std 830-1998**.
* **Objetivo Específico 3 (OE3):** Vistas de Integración de la Arquitectura de Microservicios según **ISO/IEC/IEEE 42010:2022**.
* **Mitigación de Restricciones (OE1):** Trazabilidad directa con los cuellos de botella priorizados mediante la Teoría de Restricciones (ToC: $R_1$, $R_2$, $R_3$).

---

## 2. Estructura de Archivos del Anexo 14

```text
docs/interfaces/
│
├── anexo_14_interfaces_externas.pdf         # Documento físico formal compilado (18 páginas)
├── ANEXO_14_ESPECIFICACION_INTERFACES_EXTERNAS.md # Especificación completa en Markdown
├── anexo_14_interfaces_externas.tex         # Código fuente académico en LaTeX
├── Anexo_14_Interfaces.zip                  # Paquete digital comprimido (OpenAPI + Postman)
├── build_interfaces_pdf.py                  # Script automatizado de compilación PDF (Playwright)
├── README.md                                # Índice y guía técnica de la carpeta
│
├── openapi/                                 # Contratos formales OpenAPI 3.0.3 (YAML)
│   ├── openapi_postiz.yaml                  # Servidor Postiz oficial (:5000)
│   ├── openapi_tool_postiz.yaml             # Microservicio interno tool-postiz (:8016)
│   ├── openapi_llm_gateway.yaml             # Pasarela LLM Gateway (:8003)
│   ├── openapi_tiktok_research.yaml         # TikTok Research API v2
│   ├── openapi_instagram_graph.yaml         # Instagram Graph API v21.0
│   ├── openapi_metricool.yaml               # Metricool REST API v1
│   ├── openapi_youtube_data.yaml            # Google YouTube Data API v3
│   ├── openapi_whatsapp_business.yaml       # WhatsApp Business Cloud & Slack
│   ├── openapi_hashicorp_vault.yaml         # HashiCorp Vault Secrets Engine (:8200)
│   └── openapi_minio_s3.yaml                # MinIO S3 Object Storage (:9000)
│
└── postman/                                 # Colección ejecutable de pruebas Postman
    ├── ITY_SAS_Interfaces_Externas.postman_collection.json # Colección Postman v2.1 (4 carpetas)
    └── ITY_SAS_Environment.postman_environment.json        # Variables de entorno parametrizadas
```

---

## 3. Resumen de las 10 Interfaces Catalogadas

| Identificador | Nombre de la Interfaz | Agente Responsable | Protocolo de Autenticación | SLA / Resiliencia |
|:---:|---|---|---|---|
| **IE-01** | TikTok Research API v2 | Agente 1: Ideación y Estrategia | OAuth 2.0 (Client Credentials) | P95 $\le 1.2$s / Circuit Breaker + Caché Redis |
| **IE-02** | Instagram Graph API v21.0 | Agente 1 (Ideación) y Agente 3 (Publicación) | User Access Token Larga Duración (60d) | Captura OAuthException + Alerta HITL |
| **IE-03** | Motor FFmpeg 6.1 / OpenCV 4.9 | Agente 2: Control de Calidad / Edición | Aislamiento en Docker Sandbox | $t \le 15$s por video / Validación determinista |
| **IE-04** | LLM Gateway Service (:8003) | Ambos Agentes (Ideación y Publicación) | Bearer Token interno + Vault Upstream | Caché Redis (1h/24h) + Fallback local SLM |
| **IE-05** | Metricool REST API v1 | Agente 3: Publicación (Fallback) | Header comercial `X-MC-TOKEN` | Contingencia ante caída del clúster Postiz |
| **IE-06** | HashiCorp Vault Engine (:8200) | Infraestructura Transversal | AppRole / Token `X-Vault-Token` | Cifrado AES-256-GCM / Rotación cada 90 días |
| **IE-07** | WhatsApp Cloud / Slack Webhooks | Agente 2 (Edición) y Agente 3 (Publicación) | OAuth 2.0 Bearer / Webhook Secret | Despacho en $t \le 2$s (Human-in-the-Loop) |
| **IE-08** | Google YouTube Data API v3 | Agente 3: Publicación y Scheduling | OAuth 2.0 (Google Identity) | Subida resumible de videos 16:9 y Shorts |
| **IE-09** | Prometheus Metrics Exporter | Monitoreo y Observabilidad Global | Scraping HTTP sin autenticación interna | Scraping cíclico 15s / Dashboards en Grafana |
| **IE-10** | MinIO S3 Object Storage (:9000) | Agente 2 (Edición) y Agente 3 (Publicación) | AWS Signature v4 (HMAC-SHA256) | URLs presignadas temporales para clientes |

---

## 4. Justificación y Rol de Postiz para AMBOS Agentes

### ¿Por qué Postiz y no la integración directa con Meta Business Suite?
1. **Superación de la Verificación Empresarial de Meta:** Evita trámites legales en EE.UU. que tardan entre 8 y 16 semanas para habilitar permisos en modo de producción.
2. **Mitigación del Síndrome de la Sesión Inválida:** Un demonio interno renueva automáticamente los tokens de larga duración, evitando la caducidad a los 60 días (Desviación Crítica UP-5).
3. **Unificación Multicanal:** Un solo punto de contacto para Instagram, Facebook, TikTok, LinkedIn y YouTube, suprimiendo la necesidad de mantener múltiples SDKs heterogéneos.
4. **Soberanía y Ahorro:** Código abierto autohospedable en Docker (`postiz/postiz-docker-compose`), eliminando suscripciones de SaaS comercial (\$99/mes).
5. **Cumplimiento de la Ley 1581 de 2012:** Los datos y tokens se procesan en la infraestructura local de la agencia, sin fugas a servidores de terceros.

### Interacción con el Agente de Ideación (Ideator):
* **Descubrimiento Preventivo:** Consulta `GET /integrations` antes de idear para saber qué redes sociales están activas para la marca.
* **Ingesta de Restricciones Técnicas:** Conoce las dimensiones, límites de caracteres y duraciones permitidas de cada red antes de redactar el brief.
* **Prevención de la Fatiga Publicitaria:** Revisa el historial de publicaciones pasadas para evitar repetir ángulos creativos en un ciclo de 35 a 40 días.

### Interacción con el Agente de Publicación (Publisher):
* **Variantes de Copy Multicanal:** Envía un payload unificado con textos adaptados específicamente para cada plataforma (`contents: {instagram, tiktok, linkedin}`).
* **Programación UTC de Precisión:** Envía la fecha y hora óptima calculada (`publish_at: ISO-8601 UTC`).
* **Control de Modos:** Soporta modo borrador (`draft`), programado (`schedule`) o inmediato (`immediate`).
* **Microservicio `tool-postiz` (:8016):** Intermedia y valida el aislamiento multi-tenant en PostgreSQL (`brand_channels`) para impedir que una marca publique en los canales de otra.

---

## 5. Instrucciones de Uso de la Colección de Postman

1. Extraer el archivo `Anexo_14_Interfaces.zip` o acceder directamente a la carpeta `docs/interfaces/postman/`.
2. Abrir **Postman** (v10 o superior) y pulsar **Import**.
3. Seleccionar los dos archivos:
   - `ITY_SAS_Interfaces_Externas.postman_collection.json`
   - `ITY_SAS_Environment.postman_environment.json`
4. Seleccionar el entorno **`ITY SAS Multiagent Environment`** en la esquina superior derecha.
5. Ejecutar las pruebas individuales o lanzar el **Collection Runner** para verificar la aserción de estados `200 OK` y validar los esquemas JSON de respuesta.

---

## 6. Regeneración del Documento Físico (PDF)

Para recompilar el documento PDF en cualquier momento:
```bash
python docs/interfaces/build_interfaces_pdf.py
```
El script utilizará Playwright Chromium en modo *headless* para compilar el archivo Markdown con la hoja de estilos de ingeniería y generar el PDF final numerado y maquetado profesionalmente.
