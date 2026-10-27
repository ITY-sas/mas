# Capítulo 7 — Implementación de la Prueba de Concepto (OE4)

Este directorio contiene la documentación formal, el código fuente en \LaTeX{} y los diagramas arquitectónicos y experimentales correspondientes al **Capítulo 7 de la Tesis de Maestría**, enfocado en responder literalmente al enunciado del **Objetivo Específico 4 (OE4)**:

> *"Implementar una prueba de concepto de los dos agentes en un entorno de contenedores, ejecutando una simulación con datos históricos o sintéticos, para demostrar la viabilidad técnica y evaluar el potencial de reducción de cuellos de botella."*

---

## 1. Estructura de Archivos

```
docs/capitulo 7/
├── capitulo_7_implementacion.pdf       # Documento definitivo compilado en PDF (40 páginas, 3.60 MB)
├── capitulo_7_implementacion.tex       # Código fuente del capítulo completo en LaTeX
├── build_capitulo7_pdf.py               # Script automatizado de compilación PDF (Playwright)
├── README.md                            # Esta guía de documentación y compilación
└── diagramas/                           # 42 figuras arquitectónicas, diagramas y gráficos (.png, .pdf, .mmd)
    ├── *.mmd                            # Fuentes editables en lenguaje Mermaid
    ├── *.pdf                            # Figuras vectoriales de alta resolución para LaTeX
    ├── *.png                            # Renders complementarios en mapa de bits (42 diagramas)
    ├── generate_statistical_figures.py  # Script Python (matplotlib) que genera las figuras empíricas
    └── render_all_diagrams.ps1          # Script PowerShell para renderizar los diagramas Mermaid
```

---

## 2. Índice del Capítulo y Figuras Asociadas

| Sección | Título | Figuras Clave Incluidas |
| :--- | :--- | :--- |
| **7.1** | **Introducción y Alcance de la Implementación** | **Figura 7.1:** Grafo de trazabilidad de objetivos (OE1 a OE4). |
| **7.2** | **Marco Metodológico de la Implementación** | **Figura 7.2:** Tablero Kanban con hitos macro.<br>**Figura 7.3:** Flujo de ramas Git y disparadores CI.<br>**Figura 7.4:** Pipeline de integración continua (5 etapas). |
| **7.3** | **Entorno de Desarrollo y Contenerización** | **Figura 7.5:** Estructura de directorios del monorepo.<br>**Figura 7.6:** Diagrama de despliegue en contenedores (14 servicios + BFF).<br>**Figura 7.7:** Topología de red Docker interna. |
| **7.4** | **Implementación del Supervisor (Orquestador)** | **Figura 7.8:** Grafo LangGraph del supervisor (interrupts y resume).<br>**Figura 7.9:** Secuencia completa de una tarea.<br>**Figura 7.10:** Estructura del módulo `orchestrator/`. |
| **7.5** | **Implementación del Agente de Ideación** | **Figura 7.11:** Grafo LangGraph del agente de ideación.<br>**Figura 7.12:** Secuencia con bucle de auto-reparación estructurada.<br>**Figura 7.13:** Estructura de clases del dossier (Reel y Post). |
| **7.6** | **Implementación del Agente de Publicación** | **Figura 7.15:** Grafo LangGraph del agente de publicación.<br>**Figura 7.16:** Secuencia detallada y entrega desacoplada con Postiz. |
| **7.7** | **Implementación de los Tool Services** | **Figura 7.18:** Estructura común y envelope uniforme.<br>**Figura 7.19:** Flujo de descubrimiento dinámico (Tool Discovery). |
| **7.8** | **Implementación del LLM Gateway** | **Figura 7.21:** Flujo de solicitud, caché Redis, balanceo y fallback. |
| **7.9** | **Implementación del Modelo de Datos** | **Figura 7.23:** Modelo Entidad-Relación en PostgreSQL/pgvector.<br>**Figura 7.24:** Grafo de orden de migraciones SQL (001 a 006). |
| **7.10** | **Datos Históricos y Sintéticos** | **Figura 7.25:** Proceso de anonimización y preparación del dataset.<br>**Figura 7.26:** Distribución del dataset por marca y formato. |
| **7.11** | **Escenarios de Simulación** | **Figura 7.28:** Secuencia del Escenario 1 (brief incompleto).<br>**Figura 7.29:** Secuencia del Escenario 2 (concurrencia de 15 briefs).<br>**Figura 7.30:** Diagrama de estados del Escenario 3 (fallback LLM).<br>**Figura 7.31:** Secuencia del Escenario 4 (caída y recuperación RabbitMQ). |
| **7.12** | **Instrumentación y Métricas** | **Figura 7.32:** Pipeline de telemetría y recolección de métricas. |
| **7.13** | **Resultados de la Simulación** | **Figura 7.34:** Comparación tiempo de ciclo (Manual vs. PoC).<br>**Figura 7.35:** Tasa de éxito por escenario.<br>**Figura 7.36:** Distribución de latencias por nodo de ejecución.<br>**Figura 7.37:** Comparación de retrabajo operativo.<br>**Figura 7.38:** Cronograma Gantt de recuperación en Escenario 4. |
| **7.14** | **Evaluación de Reducción de Cuellos** | **Figura 7.40:** Mitigación de cuellos de botella del OE1 (R1, R2, R3).<br>**Figura 7.41:** Diagrama de brecha (diseñado vs. implementado vs. producción). |
| **7.15** | **Validación de la Hipótesis** | **Figura 7.42:** Árbol de hipótesis y veredicto de validación.<br>**Figura 7.43:** Contraste con las metas fijadas ($H_1$, $H_{1.1}$ a $H_{1.4}$). |
| **7.16** | **Validación con Stakeholders** | **Figura 7.44:** Guion de demostración técnica operado con ITY SAS. |
| **7.17** | **Manual de Simulación** | **Figura 7.45:** Árbol de decisión para diagnóstico de problemas. |
| **7.18** | **Conclusiones del Capítulo** | **Figura 7.46:** Diagrama de cumplimiento del OE4 (compromiso vs. entrega). |

---

## 3. Instrucciones de Generación y Compilación

### 3.1. Regenerar los Gráficos Estadísticos (Python)
Desde la raíz del proyecto:
```bash
python "docs/capitulo 7/diagramas/generate_statistical_figures.py"
```
Esto genera las figuras vectoriales `.pdf` y los mapas de bits `.png` para las figuras estadísticas (7.26, 7.34, 7.35, 7.36, 7.37, 7.40 y 7.43).

### 3.2. Regenerar los Diagramas Mermaid
Requisitos: Node.js con `npx`.
```powershell
powershell -ExecutionPolicy Bypass -File "docs/capitulo 7/diagramas/render_all_diagrams.ps1"
```

### 3.3. Compilar el Documento LaTeX
Desde la carpeta `docs/capitulo 7/`:
```bash
pdflatex capitulo_7_implementacion.tex
pdflatex capitulo_7_implementacion.tex
```
*(La segunda pasada resuelve referencias cruzadas, etiquetas `\ref{...}` y numeración de tablas y figuras).*
