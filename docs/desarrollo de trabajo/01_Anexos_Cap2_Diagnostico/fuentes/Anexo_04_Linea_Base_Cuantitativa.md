# Anexo 4. Línea Base Cuantitativa: Tablas de Tiempos y Retrabajo

<div class="meta">
<b>Capítulo:</b> 2 (Diagnóstico Operativo) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE1 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Introducción y Ficha Técnica de la Muestra

El establecimiento de la línea base cuantitativa del proceso de producción de contenidos en ITY SAS se sustentó en un diseño metodológico mixto que combinó el censo documental retrospectivo de las órdenes ejecutadas durante el primer semestre de 2026 y el cronometraje estratificado en tiempo real durante sesiones de observación directa (*Gemba Walk*).

### Ficha Técnica del Muestreo:
* **Población Total (Censo Documental):** $N = 315$ piezas publicadas entre enero y julio de 2026.
* **Muestra Cronometrada en Campo:** $n = 166$ piezas monitoreadas directamente con registro de tiempos de ciclo activo ($T_p$) y tiempos de espera ($T_w$).
* **Estratificación de la Muestra:**
  * **Reels (Video Corto):** $n_1 = 68$ piezas (41,0%).
  * **Posts Estáticos:** $n_2 = 54$ piezas (32,5%).
  * **Carruseles / Infografías:** $n_3 = 44$ piezas (26,5%).
* **Instrumento de Registro:** Archivo maestro `Anexo_04_Plantilla_Recoleccion_Tiempos_Retrabajo_166_Casos.xlsx` estructurado en cuatro hojas de cálculo vinculadas.

---

## 2. Acumulado de Horas por Macrofase y Formato (Muestra n=166)

La tabla desagrega las horas dedicadas por el personal de la agencia agrupadas en las cuatro macrofases del flujo de trabajo:

| Macrofase Operativa | Pasos Incluidos | Reels (n=68) | Posts (n=54) | Carruseles (n=44) | Total Horas | % del Tiempo |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Fase 1: Análisis y Preproducción** | Pasos 1, 2, 3, 4 y 5 | 184,28 h | 66,42 h | 80,52 h | 331,22 h | 12,2% |
| **Fase 2: Edición y Ensamble** | Pasos 6, 7 y 8 | 1.156,68 h | 125,82 h | 212,52 h | 1.495,02 h | 55,1% |
| **Fase 3: Espera y Retrabajos** | Pasos 10 y 11 | 486,88 h | 114,48 h | 164,56 h | 765,92 h | 28,2% |
| **Fase 4: Distribución y Meta Suite** | Pasos 12, 13, 14, 15 y 16 | 48,96 h | 34,02 h | 37,84 h | 120,82 h | 4,5% |
| **TOTALES ACUMULADOS** | **Pasos 1 al 16** | **1.876,80 h** | **340,74 h** | **495,44 h** | **2.712,98 h** | **100,0%** |

---

## 3. Promedios de Tiempos de Ciclo ($T_p$) y Esperas ($T_w$) por Pieza

Para contrastar la eficiencia entre los distintos entregables, la tabla presenta las medias aritméticas y desviaciones estándar expresadas en horas por pieza:

| Dimensión Temporal | Reels (Horas/Pieza) | Posts (Horas/Pieza) | Carruseles (Horas/Pieza) | Promedio Ponderado |
|---|:---:|:---:|:---:|:---:|
| **Tiempo de Ciclo Activo ($T_p$)** | 19,72 h ($\pm 4,12$) | 3,56 h ($\pm 0,85$) | 6,66 h ($\pm 1,45$) | **11,01 h** |
| **Tiempo de Espera en Cola ($T_w$)** | 115,22 h ($\pm 28,4$) | 38,40 h ($\pm 9,2$) | 54,60 h ($\pm 12,8$) | **74,18 h** |
| **Tiempo Total de Entrega ($LT$)** | **134,94 h** | **41,96 h** | **61,26 h** | **85,19 h** |
| **Eficiencia de Ciclo ($PCE$)** | **14,6%** | **8,5%** | **10,9%** | **12,9%** |

---

## 4. Análisis de la Tasa de Retrabajo y Distribución de Revisiones

El retrabajo representa el mayor generador de desperdicio y costo oculto en ITY SAS. Se computaron los ciclos de devolución interna (Paso 8) y externa por parte del cliente (Paso 10):

| Métrica de Calidad y Retrabajo | Reels (n=68) | Posts (n=54) | Carruseles (n=44) | Total Muestra (n=166) |
|---|:---:|:---:|:---:|:---:|
| **Piezas sin retrabajo (0 revisiones)** | 12 (17,6%) | 24 (44,4%) | 16 (36,4%) | 52 (31,3%) |
| **Piezas con 1 ciclo de revisión** | 22 (32,4%) | 18 (33,3%) | 17 (38,6%) | 57 (34,3%) |
| **Piezas con 2 ciclos de revisión** | 20 (29,4%) | 9 (16,7%) | 8 (18,2%) | 37 (22,3%) |
| **Piezas con 3 o más revisiones** | 14 (20,6%) | 3 (5,6%) | 3 (6,8%) | 20 (12,1%) |
| **Tasa Global de Retrabajo ($TR$)** | **82,4%** | **55,6%** | **63,6%** | **68,7%** |
| **Promedio de Revisiones por Pieza** | **2,23 rev/pieza** | **0,83 rev/pieza** | **0,95 rev/pieza** | **1,44 rev/pieza** |

---

## 5. Taxonomía y Distribución Causal de los Motivos de Retrabajo

A partir de la auditoría de 436 incidentes de modificación registrados en las 166 piezas analizadas, se estructuró la siguiente taxonomía de fallos:

| Código | Motivo de Retrabajo / Defecto | Frecuencia Absoluta | Porcentaje (%) | Causa Raíz Identificada en el Proceso |
|:---:|---|:---:|:---:|---|
| **MOT-1** | Cambios de enfoque conceptual / brief desalineado | 262 | 60,1% | Brief inicial recibido de forma ambigua por notas de voz o mensajes informales. |
| **MOT-2** | Inconsistencias de copy, ortografía y hashtags | 83 | 19,0% | Falta de validación ortográfica automática y desalineación con la guía de estilo. |
| **MOT-3** | Ajustes estéticos, tipografía y paleta de color | 65 | 14,9% | Falta de control estricto de brand guidelines antes de la entrega al cliente. |
| **MOT-4** | Reemplazo de música, derechos de autor o formato | 26 | 6,0% | Selección de audios virales sin verificación previa de licencias comerciales. |
| **TOTAL** | **Incidentes de retrabajo documentados** | **436** | **100,0%** | **El 79,1% de los errores se originan en las fases 1 y 2.** |

---

## 6. Conclusiones y Trazabilidad de la Línea Base

1. **El formato Reel es el mayor demandante de capacidad:** Concentra el 69,2% de todas las horas invertidas en la agencia y presenta una tasa de retrabajo crítica del 82,4%, con un tiempo de entrega medio de 134,94 horas (5,6 días continuos).
2. **El origen del desperdicio es conceptual, no técnico:** El 60,1% del retrabajo se debe a discrepancias entre la expectativa del cliente y el contenido producido, confirmando que la ideación y el briefing constituyen el punto más vulnerable de la operación.
3. Esta línea base cuantificada valida los umbrales de éxito fijados para el sistema multiagente: reducción del tiempo de ciclo $\ge 20\%$ y disminución de la tasa de retrabajo $\ge 25\%$.
