# Entregable Oficial 2.1: Documento de Diagnóstico de Cuellos de Botella (VSM y ToC)

## Sistema Multiagente para la Optimización del Proceso de Producción de Contenido Digital — ITY SAS
### Universidad Católica de Colombia — Facultad de Ingeniería (2026)
**Autor:** Alvaro Felipe Lopez Russi (Código 67000867)  
**Vinculación:** Cumplimiento formal del **Objetivo Específico 1 (OE1)** del Trabajo de Grado.

---

## 1. Descripción del Entregable

Este directorio contiene el **Documento de Diagnóstico Operativo** completo y formal elaborado a partir del Capítulo 2 del trabajo de grado, integrando con rigor ingenieril las metodologías **Value Stream Mapping (VSM)** y la **Teoría de Restricciones (ToC)** de Eliyahu Goldratt.

El diagnóstico se fundamenta en un levantamiento censal de campo realizado durante cuatro semanas continuas (1 al 28 de agosto de 2026) sobre **315 piezas de contenido** producidas para 10 cuentas comerciales activas de la agencia ITY SAS en Bogotá D.C. El análisis abarca **29.150,23 horas de procesamiento activo**, **9.632,97 horas de esperas pasivas**, una encuesta psicométrica de carga laboral (escala Likert de 15 ítems, $\alpha = 0,884$) aplicada a 10 colaboradores (T1 a T10) y 5 días de observación directa estructurada.

---

## 2. Estructura de Archivos del Entregable

| Archivo | Formato | Tamaño / Extensión | Descripción Técnica |
|---|:---:|:---:|---|
| [**`DOCUMENTO_DIAGNOSTICO_VSM_TOC.md`**](DOCUMENTO_DIAGNOSTICO_VSM_TOC.md) | Markdown | ~214 KB (~25.000 palabras) | **Documento exhaustivo integral** con los 12 capítulos desarrollados en profundidad, 22 tablas completas, formulación matemática KaTeX, citas bibliográficas y 5 anexos técnicos. |
| [**`documento_diagnostico_vsm_toc.pdf`**](documento_diagnostico_vsm_toc.pdf) | PDF (A4) | **4,46 MB (64 páginas)** | **Documento formal compilado en PDF** con diseño editorial académico, portada institucional, firmas de jurado, tabla de contenido, encabezados y pies de página (`Página X de Y`) y 11 diagramas de alta resolución. |
| [**`documento_diagnostico_vsm_toc.tex`**](documento_diagnostico_vsm_toc.tex) | LaTeX | ~12 KB | Archivo fuente LaTeX listo para compilar con `pdflatex` o en plataformas académicas como Overleaf. |
| [**`build_diagnostico_pdf.py`**](build_diagnostico_pdf.py) | Python Script | ~13 KB | Script automatizado que utiliza Playwright Chromium para compilar el Markdown a PDF con soporte matemático KaTeX. |
| [**`graficas/`**](graficas/) | Directorio | 11 Archivos PNG | Carpeta con todas las figuras analíticas generadas a 300 DPI (Histogramas, VSM Macro, VSM Micro, Ishikawa 6M, Matriz ToC, Curva Estocástica e Índice IA). |

---

## 3. Catálogo de Figuras y Diagramas Incluidos en `graficas/`

1. **`fig_01_horas_por_fase.png`** (Figura 5.1): Distribución total de horas acumuladas por fase y formato en ITY SAS ($N=315$ piezas).
2. **`fig_02_promedios_por_pieza.png`** (Figura 5.2): Comparación de tiempos unitarios por pieza ($C/T$) y frecuencia media de retrabajo por formato.
3. **`fig_03_encuesta_likert.png`** (Figura 6.1): Resultados de la encuesta de carga laboral (Medias y Desviaciones Estándar de 10 colaboradores).
4. **`fig_04_matriz_priorizacion.png`** (Figura 8.1): Matriz estratégica de priorización de restricciones operativas ToC (Impacto vs Control Interno).
5. **`fig_05_curva_edicion_retrabajo.png`** (Figura 9.2): Curva del tiempo de ciclo esperado $E[TC]$ en función de la probabilidad de rechazo $P(R_1)$.
6. **`fig_06_indice_automatizacion.png`** (Figura 10.1): Evaluación de factibilidad técnica mediante el Índice de Automatización ($IA$).
7. **`fig_07_vsm_comparacion_as_is_to_be.png`** (Figura 11.1): Comparativa de tiempos de ciclo y Lead Time: Escenario As-Is vs Estado Futuro To-Be.
8. **`fig_08_diagrama_flujo_16_pasos.png`** (Figura 3.1): Diagrama de flujo detallado del proceso As-Is (16 pasos secuenciales y 4 macrociclos).
9. **`fig_09_vsm_macro_diagram.png`** (Figura 7.1): Value Stream Mapping (VSM) Macro Agregado del estado actual en ITY SAS.
10. **`fig_10_vsm_micro_edicion.png`** (Figura 9.1): Micro-VSM del subproceso de edición de Reels y bucle de retrabajo interno.
11. **`fig_11_ishikawa_cuellos_botella.png`** (Figura 8.2): Diagrama de Causa y Efecto (Ishikawa 6M) de las ineficiencias operativas.

---

## 4. Síntesis de Hallazgos y Matriz de Priorización de Restricciones

### 4.1. Indicadores Globales de la Cadena de Valor (VSM As-Is)
- **Tiempo de Valor Agregado ($VA$):** $29.150,23$ horas ($92,54$ h/pieza en promedio).
- **Tiempo de No Valor Agregado ($NVA$):** $9.632,97$ horas ($30,58$ h/pieza en promedio).
- **Lead Time Total del Sistema:** $38.783,20$ horas ($123,12$ h/pieza en promedio).
- **Eficiencia del Ciclo de Proceso ($PCE$):** $75,16\%$ (Eficiencia aparente distorsionada por 436 ciclos de retrabajo interno; eficiencia real $< 60,0\%$).

### 4.2. Matriz de Criticidad de Restricciones (Teoría de Restricciones)
El Índice de Criticidad ($IC = I + F + C$, escala de 3 a 15) jerarquizó las restricciones del sistema:

| ID | Restricción Operativa | Impacto ($I$) | Frecuencia ($F$) | Control ($C$) | Índice $IC$ | Prioridad / Acción en el Sistema Multiagente |
|:---:|---|:---:|:---:|:---:|:---:|---|
| **$R_1$** | **Bucle de Edición de Video (Reels):** Retrabajo por controles informales ($C/T = 134,94$ h/pza, 2,23 rev/pza). | 5 | 5 | 5 | **15 / 15** | **PRIORIDAD 1 (Restricción Primaria)**<br>Abordada por el Agente de Edición y Control de Calidad ($IA=5,0$). |
| **$R_2$** | **Ineficiencia en Ideación y Briefing:** Información rota que origina el $60\%$ de los reprocesos ($C/T = 19,03$ h/pza). | 4 | 5 | 5 | **14 / 15** | **PRIORIDAD 2 (Restricción Secundaria)**<br>Abordada por el Agente de Ideación y RAG ($IA=4,3$). |
| **$R_3$** | **Publicación Manual Multicanal:** Tareas repetitivas que generan 125,63 h de retraso en última milla. | 3 | 4 | 5 | **12 / 15** | **PRIORIDAD 3 (Restricción Terciaria)**<br>Abordada por el Agente de Publicación ($IA=5,0$). |
| **$R_4$** | **Espera por Aprobación del Cliente:** Inactividad pasiva de $6.032,97$ horas ($19,15$ h/pza). | 5 | 5 | 1 | **11 / 15** | **EXCLUIDA DE LA AUTOMATIZACIÓN**<br>Restricción exógena ($IA=2,0$). Gestión mediante acuerdos SLA de 24h. |

### 4.3. Modelado Estocástico de la Restricción $R_1$ (Edición de Video)
$$TC_{\text{Real}} = TC_{\text{Base}} + P(R_1) \cdot TC_{R1} + P(R_2) \cdot TC_{R2} = 6,0 + (0,60 \times 2,5) + (0,30 \times 1,5) = 7,95\text{ h/pieza}$$
- El retrabajo incrementa el tiempo de edición en un **$+32,5\%$**, generando **$2.366,19$ horas mensuales de desperdicio evitable**.
- La automatización de chequeos de calidad reduce $P(R_1)$ a $0,10$, bajando el tiempo a **$6,70$ h/pza** ($-15,7\%$) y recuperando **$1.314$ horas mensuales** de capacidad técnica.

---

## 5. Instrucciones para Recompilar el Documento PDF

Para volver a generar el documento PDF en caso de ajustes en los datos o textos:

```bash
# 1. Asegurar dependencias de Python y Playwright
python -m pip install playwright matplotlib seaborn pandas numpy
playwright install chromium

# 2. Re-generar las gráficas analíticas (si hubo cambios)
python generar_graficas_diagnostico.py
python generar_diagramas_vsm.py

# 3. Compilar el documento PDF de 64 páginas
python docs/documento_diagnostico/build_diagnostico_pdf.py
```

El script validará automáticamente el tiempo de carga, renderizará las fórmulas KaTeX y reportará el número exacto de páginas compiladas en la terminal.
