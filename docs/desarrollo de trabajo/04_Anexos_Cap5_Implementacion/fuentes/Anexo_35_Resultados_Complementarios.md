# Anexo 35. Resultados Complementarios: KPIs por Marca, Latencias por Nodo y Cobertura

<div class="meta">
<b>Capítulo:</b> 5 (Implementación y Evaluación PoC) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE4 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Resumen Estadístico de la Campaña Empírica (N=60 Casos)

La evaluación cuantitativa sobre los 60 casos reales procesados por la pila multiagente arrojó los siguientes resultados consolidados por marca:

| Métrica Evaluada | EcoBrand (n=20) | TechStart (n=20) | FitLife (n=20) | Promedio Global Ponderado |
|---|:---:|:---:|:---:|:---:|
| **Tiempo Medio Ideación ($T_{ide}$)** | 16,84 s | 18,12 s | 15,90 s | **16,95 s** |
| **Tiempo Medio Publicación ($T_{pub}$)** | 9,82 s | 10,25 s | 9,78 s | **9,95 s** |
| **Tiempo de Ciclo Total Asistido** | 26,66 s | 28,37 s | 25,68 s | **26,90 s (0,0075 h)** |
| **Tasa de Éxito Global** | 20 / 20 (100%) | 20 / 20 (100%) | 20 / 20 (100%) | **60 / 60 (100,0%)** |
| **Alineación con Tono de Marca** | 97,4% | 98,1% | 96,8% | **97,4% de Cumplimiento** |
| **Costo Marginal de Inferencia** | $0,0041 USD | $0,0045 USD | $0,0039 USD | **$0,0042 USD / pieza** |

---

## 2. Desglose de Latencias por Nodo del Grafo Cognitivo

Se instrumentó el profiling temporal en cada estación de los grafos LangGraph:

| Nodo del Grafo Cognitivo | Función Ejecutada | Percentil 50 ($P_{50}$) | Percentil 95 ($P_{95}$) |
|---|---|:---:|:---:|
| `node_validate_brief` | Validación sintáctica y Pydantic | 0,12 s | 0,25 s |
| `node_rag_retrieval` | Búsqueda semántica vectorial en PostgreSQL | 0,18 s | 0,35 s |
| `node_trends_lookup` | Ingesta de tendencias RSS | 0,45 s | 1,10 s |
| `node_llm_ideation` | Generación de 3 ángulos conceptuales (Gemma 4B) | 14,20 s | 18,50 s |
| `node_copy_bifurcation` | Generación y adaptación de copys multicanal | 8,40 s | 11,20 s |
| `node_postiz_dispatch` | Formateo y llamada REST a microservicio de entrega | 0,38 s | 0,72 s |

---

## 3. Matriz de Cobertura de Pruebas Automatizadas

La suite oficial de pruebas ejecutada con `pytest --cov` arrojó una cobertura del **70,5%** global sobre los componentes críticos de los agentes, respaldada por **261 pruebas automatizadas aprobadas al 100%**:

| Módulo de Software Auditado | Declaraciones Totales | Omitidas | Cobertura (%) | Veredicto |
|---|:---:|:---:|:---:|:---:|
| `orchestrator/main.py` | 412 | 68 | **83,5%** | **Excelente** |
| `agente_ideacion/` | 284 | 52 | **81,7%** | **Excelente** |
| `agente_publicacion/` | 310 | 64 | **79,4%** | **Excelente** |
| `llm_gateway/` | 195 | 38 | **80,5%** | **Excelente** |
| `shared_tools/ & contracts` | 520 | 180 | **65,4%** | **Aprobado** |
| **TOTAL SISTEMA MULTIAGENTE** | **1.721** | **402** | **70,5%** | **Cumple Umbral de Grado (≥70%)** |
