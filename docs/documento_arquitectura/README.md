# Entregable: Documento de Arquitectura de Software (SAD)
## Sistema Multiagente para la Optimización del Proceso de Producción de Contenido Digital — ITY SAS

Este directorio contiene el **Documento de Arquitectura de Software** formal del Sistema Multiagente de ITY SAS, elaborado a partir del Capítulo 6, Capítulo 7, el código del repositorio y alineado 100% con la **Especificación de Requisitos de Software (SRS) conforme al estándar IEEE Std 830-1998** (Revisión 1.0, 5 de septiembre de 2026).

El documento sigue la estructura internacional de la plantilla **arc42 (Versión 7.0 ES)** y se alinea con la norma **ISO/IEC/IEEE 42010:2022**.

---

## Archivos del Entregable

| Archivo | Formato | Descripción |
|---|:---:|---|
| [**`documento_arquitectura.pdf`**](documento_arquitectura.pdf) | PDF (1.26 MB, 36 págs) | **Documento definitivo formal compilado** con portada arc42, 19 diagramas embebidos, tablas completas IEEE 830, métricas y escenarios ATAM. Disponible también directamente en `docs/documento_arquitectura.pdf`. |
| [**`DOCUMENTO_ARQUITECTURA.md`**](DOCUMENTO_ARQUITECTURA.md) | Markdown (64 KB) | **Documento integral de arquitectura de software** para visualización directa en GitHub, VS Code o renderizado a HTML/PDF. Contiene las 12 secciones completas, diagramas embebidos, tablas de requisitos oficiales, explicaciones de qué/cómo/por qué y matrices. |
| [**`build_arquitectura_pdf.py`**](build_arquitectura_pdf.py) | Python Script | Script automatizado con Playwright Chromium para compilar el documento Markdown en PDF A4 de alta calidad. |
| [**`documento_arquitectura.tex`**](documento_arquitectura.tex) | LaTeX (~34 KB) | Código fuente LaTeX formal del documento de arquitectura listo para Overleaf o TeXLive. |
| **`images/`** | Directorio | Carpeta con **20 diagramas de alta resolución PNG/PDF** y el logotipo oficial de arc42 (`arc42-logo.png`). |

---

## Alineación con la SRS IEEE Std 830-1998 (ITY SAS)

El documento incorpora con total fidelidad el catálogo oficial de requisitos:
1. **Cuellos de Botella de Fase 1 (OE1)**:
   - **R1: Bucle de edición y retrabajo interno (IC = 15/15)**: Cubierto por **REQ-F11 a REQ-F20** e interfaces `REQ-IE03`, `REQ-IE07`, `REQ-IE10`.
   - **R2: Ineficiencia en ideación y estrategia (IC = 14/15)**: Cubierto por **REQ-F01 a REQ-F10** e interfaces `REQ-IE01`, `REQ-IE02`, `REQ-IE04`.
   - **R3: Adaptación manual para publicación multicanal (IC = 12/15)**: Cubierto por **REQ-F21 a REQ-F30** e interfaces `REQ-IE04`, `REQ-IE05`, `REQ-IE08`, `REQ-IE10`.
2. **49 Requisitos Totales Priorizados con MoSCoW**:
   - **30 Requisitos Funcionales**: Agente 1 (Ideación, REQ-F01 a REQ-F10), Agente 2 (Edición, REQ-F11 a REQ-F20) y Agente 3 (Publicación, REQ-F21 a REQ-F30).
   - **10 Interfaces de Software Externas**: REQ-IE01 a REQ-IE10 (TikTok Research, Instagram Graph, FFmpeg/OpenCV, LLM, Metricool/Postiz, Vault, Slack/WhatsApp, YouTube Data, Prometheus, S3/MinIO).
   - **9 Requisitos No Funcionales**: REQ-NF01 a REQ-NF09 (Contenedores $\le 500$ MB, latencia $<500$ ms, disponibilidad 99,5\%, Vault AES-256, HPA $10\times$, logs 90 días, fallback, startup $<15$ s, Ley 1581 de 2012).
3. **Validación con Stakeholders (Anexo B del SRS)**: Taller de co-creación de 2 horas con 93,9% de consenso inicial y 100% formal tras ajustes menores (REQ-F03, REQ-F16, REQ-NF07), superando el umbral del 90%.

---

## Catálogo de Diagramas Incluidos en `images/`

1. `01_contexto` (C4 Nivel 1 Contexto)
2. `02_contenedores` (C4 Nivel 2 Contenedores)
3. `03_componentes` (C4 Nivel 3 Componentes Integrados)
4. `04_secuencia_pipeline` (Secuencia AUML del Pipeline E2E)
5. `05_despliegue` (C4 Nivel 4 Despliegue de Infraestructura)
6. `06_modelo_datos` (Modelo Entidad-Relación de Datos en PostgreSQL 16)
7. `07_grafos_agentes` (Nodos y Transiciones de Grafos LangGraph)
8. `08_tool_discovery` (Descubrimiento Dinámico de Herramientas vía Manifiesto)
9. `09_bdi_flujo` (Flujo Deliberativo BDI y Auto-reparación)
10. `10_rag_multi_tenant` (Flujo RAG Multi-Tenant con Filtro por Marca)
11. `11_secuencia_publicacion_postiz` (Secuencia de Publicación hacia Postiz API)
12. `12_secuencia_fallo_recuperacion` (Manejo de Caídas y Recuperación con Checkpoints)
13. `13_arquitectura_evolucion` (Síntesis de la Ruta de Generación Implementada)
14. `14_roadmap_capacidades` (Roadmap de Evolución hacia Arquitectura Productiva)
15. `15_architecture-decisions` (Mapa de Decisiones de Arquitectura ADR)
16. `16_quality_scenarios` (Resumen Visual de Escenarios de Calidad ATAM)
17. `17_vincular_canal_postiz` (Secuencia de Consulta y Vinculación de Canales Postiz)
18. `18_frontend_modulos` (Módulos de la SPA React 19 y Relación con el BFF)
19. `19_estados_publicacion` (Máquina de Estados Finita de Publicaciones)
