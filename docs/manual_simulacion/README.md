# Manual de Ejecución y Validación de la Prueba de Concepto (PoC) — ITY SAS

Este directorio contiene la documentación técnica formal, el código fuente en \LaTeX{}, el script de compilación automatizada y el documento compilado en PDF que guía al usuario (futuros desarrolladores o personal técnico de **ITY SAS**) en la ejecución de la Prueba de Concepto, en estricto cumplimiento del **Objetivo Específico 4 (OE4)** de la tesis de maestría:

> *"Implementar una prueba de concepto de los dos agentes en un entorno de contenedores, ejecutando una simulación con datos históricos o sintéticos, para demostrar la viabilidad técnica y evaluar el potencial de reducción de cuellos de botella."*

---

## 1. Estructura de Archivos del Módulo

```text
docs/manual_simulacion/
├── manual_ejecucion_poc_multiagente.pdf  # Documento final en PDF (25 páginas, diagramas y fórmulas KaTeX)
├── manual_ejecucion_poc_multiagente.tex  # Código fuente completo en LaTeX
├── build_manual_pdf.py                  # Script Python automatizado para compilar a PDF vía Playwright
├── README.md                            # Guía técnica y explicación de artefactos
└── diagramas/                           # Figuras arquitectónicas, secuencias y gráficos empíricos
    ├── *.mmd                            # Fuentes editables en lenguaje Mermaid
    ├── *.pdf                            # Figuras vectoriales de alta resolución
    └── *.png                            # Renders de mapa de bits para inserción en documentos
```

---

## 2. Contenido del Manual

El manual está estructurado en 8 secciones técnicas exhaustivas:

1. **Vinculación Formal con el Objetivo Específico 4 (OE4):** Declaración literal, contexto de la agencia digital ITY SAS, caracterización de los tres cuellos de botella del diagnóstico OE1 (R1: Retrabajo editorial, R2: Lentitud en Fase 1, R3: Dispersión multicanal), matriz de hipótesis de investigación y metas cuantitativas de los tres KPIs.
2. **Requisitos Técnicos y Arquitectura del Entorno:** Especificaciones mínimas y recomendadas de hardware (CPU, RAM, SSD), software base (Docker Desktop, Python 3.10+, Ollama), topología detallada de los 14 microservicios contenerizados, redes internas Docker y gestión segura de secretos en el archivo `.env`.
3. **Guía de Comandos Paso a Paso:** Comandos para descargar modelos en Ollama (`gemma3:4b`, `mistral-nemo`, `nomic-embed-text`), levantar Postiz, compilar y encender la pila con `docker compose up -d --build`, verificar healthchecks, aplicar migraciones SQL en PostgreSQL, cargar datos semilla (`seed_data.py`), ejecutar la suite de pruebas automatizadas (`pytest`) y arrancar Studio (BFF en puerto 3001).
4. **Descripción Exhaustiva de los Escenarios de Simulación:** Justificación y detalle técnico de los cinco escenarios de estrés:
   - **E1: Brief Incompleto y Auto-reparación Estructurada** (LangGraph self-repair loop en 1 pasada).
   - **E2: Sobrecarga Concurrente de Tareas** (15 briefs concurrentes, absorción en RabbitMQ y TaskStore en Redis).
   - **E3: Fallo y Fallback Automático en LLM Gateway** (Conmutación transparente de Gemma 3 a Mistral NeMo).
   - **E4: Caída Forzada de Broker RabbitMQ y Recuperación** (Persistencia distribuida de checkpoints en Redis Stack y redelivery at-least-once).
   - **E5: Aislamiento Multi-Tenant Estricto en pgvector** (Filtro por `brand_id` sin contaminación cruzada entre marcas).
5. **Interpretación y Auditoría de Logs Distribuidos:** Anatomía de logs estructurados en JSON, correlación distribuida mediante `task_id`, trazabilidad en grafos LangGraph y patrones de diagnóstico de errores.
6. **Extracción y Evaluación Formal de Métricas:** Modelación matemática con fórmulas en \LaTeX{} para Tiempo de Ciclo ($T_c$), Porcentaje de Reducción frente a la línea base manual ($\Delta T_{\%}$), Tasa de Éxito en Simulación ($S_r$), Cobertura de Pruebas Unitarias ($C_u$) e Índice Ponderado de Automatización ($I_A$), con resultados empíricos certificados sobre la campaña de 60 casos reales.
7. **Árbol de Decisión y Diagnóstico de Incidencias (Troubleshooting):** Matriz de errores frecuentes, árbol sistemático de diagnóstico en diagrama de flujo y procedimientos de restablecimiento selectivo de contenedores.
8. **Conclusiones y Recomendaciones:** Síntesis de cumplimiento del OE4 y recomendaciones técnicas para la transición a producción en Kubernetes e inferencia acelerada con GPU.

---

## 3. Métricas y KPIs Validados en la PoC

| Indicador | Métrica y Descripción | Meta Esperada | Obtenido en la PoC | Estado |
| :--- | :--- | :---: | :---: | :---: |
| **KPI 1** | **Tasa de éxito en simulación** ($S_r$) | $\ge 90\%$ | **100.0%** (60/60 casos) | **SUPERADO** |
| **KPI 2** | **Reducción de tiempo de ciclo** ($\Delta T_{\%}$) | $\ge 20\%$ | **99.97%** (Fase 1: de 18.83 h a 21.44 s) | **SUPERADO** |
| **KPI 3** | **Cobertura de pruebas unitarias** ($C_u$) | $\ge 80\%$ | **84.0%** (397/475 sentencias, 36 pruebas) | **SUPERADO** |

---

## 4. Instrucciones para Compilar y Regenerar el PDF

### Opción A: Compilación Automática con Python y Playwright (Recomendada)
Esta opción utiliza Chromium headless para compilar directamente el manual a PDF con tipografía profesional, fórmulas matemáticas renderizadas con KaTeX, encabezados, numeración dinámica de páginas y diagramas embebidos en alta definición:

```powershell
python docs/manual_simulacion/build_manual_pdf.py
```
El archivo de salida se generará en:
`docs/manual_simulacion/manual_ejecucion_poc_multiagente.pdf`

### Opción B: Compilación con LaTeX (`pdflatex` / TeX Live / Overleaf)
Si dispone de un entorno local con TeX Live, MiKTeX o en la plataforma Overleaf:

```bash
cd docs/manual_simulacion
pdflatex manual_ejecucion_poc_multiagente.tex
pdflatex manual_ejecucion_poc_multiagente.tex
```
*(Se requieren dos pasadas sucesivas para resolver las referencias cruzadas de figuras, tablas y secciones).*

### Opción C: Regenerar Diagramas Mermaid
Si modifica los diagramas `.mmd` en la carpeta `diagramas/`:

```powershell
npx --yes @mermaid-js/mermaid-cli -i "docs/manual_simulacion/diagramas/<archivo>.mmd" -o "docs/manual_simulacion/diagramas/<archivo>.png"
```
