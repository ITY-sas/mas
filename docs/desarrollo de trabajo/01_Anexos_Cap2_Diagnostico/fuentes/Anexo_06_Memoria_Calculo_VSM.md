# Anexo 6. Memoria de Cálculo del VSM (Valor Agregado y Eficiencia)

<div class="meta">
<b>Capítulo:</b> 2 (Diagnóstico Operativo) &nbsp;|&nbsp; 
<b>Objetivo Específico:</b> OE1 &nbsp;|&nbsp; 
<b>Investigador:</b> Alvaro Felipe Lopez Russi &nbsp;|&nbsp; 
<b>Entidad:</b> ITY SAS / Universidad Católica de Colombia
</div>

## 1. Introducción y Fórmulas de Cálculo

El Mapeo de la Cadena de Valor (*Value Stream Mapping* - VSM) exige una rigurosa discriminación matemática entre las actividades que transforman positivamente el contenido para el usuario y las esperas o reprocesos que consumen recursos sin generar valor. 

Este anexo consolida la memoria técnica de cálculo de los indicadores cuantitativos del estado actual (*As-Is*) en ITY SAS, calculados sobre la muestra cronometrada de $n = 166$ casos reales:

1. **Tiempo de Ciclo de Valor Agregado ($T_{va}$):** Suma exclusiva de las tareas de conceptualización aprobada a la primera, redacción efectiva, diseño visual y edición técnica final:
   $$T_{va} = \sum_{j \in VA} T_{p,j}$$

2. **Tiempo de No Valor Agregado ($T_{nva}$):** Suma de los tiempos de espera pasiva en bandejas de entrada ($T_w$) y las horas invertidas en ciclos de retrabajo por corrección ($T_{retrabajo}$):
   $$T_{nva} = \sum T_w + \sum T_{retrabajo}$$

3. **Tiempo de Entrega Total (*Lead Time* - $LT$):**
   $$LT = T_{va} + T_{nva}$$

4. **Eficiencia del Ciclo del Proceso ($PCE$):**
   $$PCE = rac{T_{va}}{LT} 	imes 100$$

---

## 2. Memoria de Cálculo Desglosada por Formato de Contenido

La siguiente matriz documenta los valores empíricos medios observados en el terreno para cada una de las tipologías de contenido:

### 2.1. Desglose para Instagram Reels ($n_1 = 68$ piezas)
* **$T_{va}$ (Valor Agregado Directo):**
  * Conceptualización y guion (Paso 3): 1,85 h
  * Grabación y rodaje en locación (Paso 6): 4,50 h
  * Edición técnica y etalonaje primer corte (Paso 7): 12,20 h
  * Redacción de copy y hashtags (Paso 9): 1,17 h
  * **Total $T_{va}$ por Reel:** **19,72 horas**
* **$T_{nva}$ (No Valor Agregado y Desperdicio):**
  * Esperas en bandejas de entrada y asignación (Pasos 1, 4, 5, 12, 13): 14,40 h
  * Bucle de retrabajo interno y externo (Pasos 8 y 11, media 2,23 rev): 38,60 h
  * Espera pasiva por visto bueno del cliente (Paso 10): 62,22 h
  * **Total $T_{nva}$ por Reel:** **115,22 horas**
* **$LT$ (Lead Time Total Reel):** $19,72 + 115,22 =$ **134,94 horas** (5,62 días continuos)
* **PCE Reel:**
  $$PCE_{Reel} = rac{19,72}{134,94} 	imes 100 = 14,61\%$$

---

### 2.2. Desglose para Posts Estáticos ($n_2 = 54$ piezas)
* **$T_{va}$ (Valor Agregado Directo):**
  * Definición de copy conceptual (Paso 3): 0,65 h
  * Diseño gráfico y diagramación (Paso 7): 2,35 h
  * Redacción de copy final (Paso 9): 0,56 h
  * **Total $T_{va}$ por Post:** **3,56 horas**
* **$T_{nva}$ (No Valor Agregado y Desperdicio):**
  * Esperas en cola de diseño y búsqueda de stock (Pasos 1, 4, 5): 6,80 h
  * Retrabajo por ajustes de color y texto (Paso 11, media 0,83 rev): 4,20 h
  * Espera pasiva por visto bueno del cliente (Paso 10): 27,40 h
  * **Total $T_{nva}$ por Post:** **38,40 horas**
* **$LT$ (Lead Time Total Post):** $3,56 + 38,40 =$ **41,96 horas** (1,75 días continuos)
* **PCE Post:**
  $$PCE_{Post} = rac{3,56}{41,96} 	imes 100 = 8,48\%$$

---

### 2.3. Desglose para Carruseles / Infografías ($n_3 = 44$ piezas)
* **$T_{va}$ (Valor Agregado Directo):**
  * Estructuración de láminas y storytelling (Paso 3): 1,20 h
  * Diseño de secuencia multi-imagen (Paso 7): 4,60 h
  * Redacción de copys complementarios (Paso 9): 0,86 h
  * **Total $T_{va}$ por Carrusel:** **6,66 horas**
* **$T_{nva}$ (No Valor Agregado y Desperdicio):**
  * Esperas en cola y revisiones preliminares: 9,50 h
  * Retrabajos por inconsistencia de datos (media 0,95 rev): 8,30 h
  * Espera pasiva de aprobación de cliente (Paso 10): 36,80 h
  * **Total $T_{nva}$ por Carrusel:** **54,60 horas**
* **$LT$ (Lead Time Total Carrusel):** $6,66 + 54,60 =$ **61,26 horas** (2,55 días continuos)
* **PCE Carrusel:**
  $$PCE_{Carrusel} = rac{6,66}{61,26} 	imes 100 = 10,87\%$$

---

## 3. Matriz Consolidada de Indicadores del VSM As-Is

La siguiente tabla resume el comportamiento operacional ponderado de la agencia ITY SAS:

| Indicador Clave de Rendimiento | Reels (n=68) | Posts (n=54) | Carruseles (n=44) | Promedio Global Ponderado |
|---|:---:|:---:|:---:|:---:|
| **Tiempo de Valor Agregado ($T_{va}$)** | 19,72 h | 3,56 h | 6,66 h | **11,01 h** |
| **Tiempo de Espera en Colas ($T_w$)** | 76,62 h | 34,20 h | 46,30 h | **54,78 h** |
| **Tiempo Invertido en Retrabajos** | 38,60 h | 4,20 h | 8,30 h | **19,40 h** |
| **Tiempo Total de No Valor Agregado ($T_{nva}$)** | 115,22 h | 38,40 h | 54,60 h | **74,18 h** |
| **Lead Time Total Promedio ($LT$)** | **134,94 h** | **41,96 h** | **61,26 h** | **85,19 h** |
| **Eficiencia de Ciclo del Proceso ($PCE$)** | **14,6%** | **8,5%** | **10,9%** | **12,1%** |

---

## 4. Interpretación de la Memoria de Cálculo

1. **La paradoja de la baja eficiencia en servicios intelectuales:** El PCE global del **12,1%** revela que por cada 100 horas que una pieza pasa en el sistema de ITY SAS, únicamente 12 horas corresponden a trabajo transformativo real; las restantes 88 horas se disipan en esperas pasivas, colas en repositorios y retrabajos no facturables.
2. **El retrabajo como NVA oculto:** Las 19,40 horas promedio dedicadas a reprocesar piezas devueltas equivalen al 176% del tiempo de valor agregado original, evidenciando que la agencia gasta más tiempo corrigiendo errores de briefing y estilo que produciendo contenido primario.
