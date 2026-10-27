import os
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

os.makedirs("docs/documento_diagnostico/graficas", exist_ok=True)
output_dir = "docs/documento_diagnostico/graficas"

# Style settings
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['axes.labelweight'] = 'bold'
plt.rcParams['figure.titlesize'] = 14

# 1. Total hours by phase and format
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
formats = ['Historias\n(n=199)', 'Posts Estáticos\n(n=45)', 'Reels\n(n=62)', 'Carruseles\n(n=9)']
x = np.arange(len(formats))
width = 0.15

analisis = [2949.64, 1287.22, 1550.39, 207.68]
diseno = [3981.65, 2495.18, 1353.13, 800.55]
edicion = [0.0, 0.0, 8366.19, 0.0]
espera = [2172.77, 1251.67, 2411.62, 196.91]
retraso = [32.86, 37.51, 49.14, 6.12]

rects1 = ax.bar(x - 2*width, analisis, width, label='Análisis/Ideación (h)', color='#2b5c8f')
rects2 = ax.bar(x - width, diseno, width, label='Diseño/Preprod (h)', color='#4682b4')
rects3 = ax.bar(x, edicion, width, label='Edición Video (h)', color='#d9534f')
rects4 = ax.bar(x + width, espera, width, label='Espera Cliente (h)', color='#f0ad4e')
rects5 = ax.bar(x + 2*width, retraso, width, label='Retraso Publ. (h)', color='#5cb85c')

ax.set_ylabel('Horas Totales Acumuladas (Agosto 2026)')
ax.set_title('Figura 5.1: Distribución Total de Horas por Fase y Formato en ITY SAS (N=315 piezas)')
ax.set_xticks(x)
ax.set_xticklabels(formats)
ax.legend(loc='upper right', frameon=True)
ax.grid(True, linestyle='--', alpha=0.5)

# Add text on top of the largest bar
ax.annotate('8.366,19 h\n(Restricción Crítica R1)', 
            xy=(2, 8366.19), xytext=(2, 9200),
            ha='center', fontweight='bold', color='#d9534f',
            arrowprops=dict(arrowstyle='->', color='#d9534f', lw=1.5))

plt.tight_layout()
plt.savefig(os.path.join(output_dir, "fig_01_horas_por_fase.png"))
plt.close()

# 2. Average hours per piece and revisions
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), dpi=300)

categories = ['Historias', 'Posts Est.', 'Reels', 'Carruseles']
c_analisis = [14.82, 28.60, 25.01, 23.08]
c_diseno = [20.01, 55.45, 21.82, 88.95]
c_edicion = [0.0, 0.0, 134.94, 0.0]
c_espera = [10.92, 27.81, 38.90, 21.88]

x_cat = np.arange(len(categories))
w = 0.2

ax1.bar(x_cat - 1.5*w, c_analisis, w, label='Análisis (h/pza)', color='#2b5c8f')
ax1.bar(x_cat - 0.5*w, c_diseno, w, label='Diseño (h/pza)', color='#4682b4')
ax1.bar(x_cat + 0.5*w, c_edicion, w, label='Edición (h/pza)', color='#d9534f')
ax1.bar(x_cat + 1.5*w, c_espera, w, label='Espera Cliente (h/pza)', color='#f0ad4e')
ax1.set_ylabel('Horas Promedio por Pieza')
ax1.set_title('Promedios Operativos por Pieza')
ax1.set_xticks(x_cat)
ax1.set_xticklabels(categories)
ax1.legend(loc='upper left', fontsize=8)
ax1.grid(True, linestyle='--', alpha=0.5)

revis_prom = [1.00, 1.93, 2.23, 1.33]
colors_rev = ['#5cb85c', '#f0ad4e', '#d9534f', '#4682b4']
bars2 = ax2.bar(categories, revis_prom, color=colors_rev, width=0.5, edgecolor='black', linewidth=0.8)
ax2.set_ylabel('Número Promedio de Revisiones')
ax2.set_title('Rondas de Retrabajo / Correcciones por Formato')
ax2.set_ylim(0, 3.0)
ax2.axhline(1.0, color='gray', linestyle=':', label='Happy Path (1.0 rev)')
for bar in bars2:
    yval = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2.0, yval + 0.08, f'{yval:.2f}', ha='center', va='bottom', fontweight='bold')
ax2.legend()
ax2.grid(True, linestyle='--', alpha=0.5)

plt.suptitle('Figura 5.2: Comparación de Tiempos Unitarios y Frecuencia de Retrabajo', y=1.02)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "fig_02_promedios_por_pieza.png"))
plt.close()

# 3. Likert Survey
fig, ax = plt.subplots(figsize=(11, 7), dpi=300)
items = [
    "1. Disposición a adoptar herramientas de IA/automatización",
    "2. La espera por aprobación de clientes retrasa el flujo",
    "3. Briefs más estructurados y completos reducirían retrabajo",
    "4. El feedback de clientes por WhatsApp/correo es caótico",
    "5. Se requieren herramientas de programación automática",
    "6. Existe alta dependencia de tareas manuales repetitivas",
    "7. Se percibe un exceso de revisiones y correcciones",
    "8. La preproducción y recolección de referencias es lenta",
    "9. Existen cuellos de botella claramente identificables",
    "10. Ausencia de plantillas y componentes estandarizados",
    "11. Interrupciones constantes en tareas creativas profundas",
    "12. Sobrecarga cognitiva y fatiga por volumen de publicaciones",
    "13. Desconexión operativa entre Trello, Drive, Meta y Canva",
    "14. Retrasos recurrentes en el cronograma pactado de entrega",
    "15. El cliente realiza solicitudes por fuera del alcance pactado"
]
means = [4.9, 4.8, 4.8, 4.7, 4.7, 4.6, 4.5, 4.4, 4.4, 4.2, 4.1, 4.3, 4.5, 4.2, 4.4]
stds = [0.31, 0.42, 0.42, 0.48, 0.48, 0.51, 0.52, 0.69, 0.51, 0.63, 0.57, 0.67, 0.53, 0.63, 0.52]

y_pos = np.arange(len(items))
ax.barh(y_pos, means, xerr=stds, align='center', color='#337ab7', ecolor='#d9534f', capsize=4, alpha=0.85, edgecolor='black', height=0.6)
ax.set_yticks(y_pos)
ax.set_yticklabels(items)
ax.invert_yaxis()
ax.set_xlabel('Puntuación Media (Escala Likert 1 a 5: 1=Total desacuerdo, 5=Total acuerdo)')
ax.set_title('Figura 6.1: Resultados de la Encuesta de Diagnóstico y Carga Laboral (N=10 Colaboradores T1-T10)')
ax.set_xlim(1.0, 5.2)
ax.axvline(4.0, color='red', linestyle='--', label='Umbral de Criticidad Severa (>= 4.0)')

for i, (m, s) in enumerate(zip(means, stds)):
    ax.text(m + s + 0.08, i, f'x̄={m:.1f} (σ={s:.2f})', va='center', fontsize=8, fontweight='bold')

ax.legend(loc='lower right')
ax.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "fig_03_encuesta_likert.png"))
plt.close()

# 4. Prioritization Matrix (ToC)
fig, ax = plt.subplots(figsize=(9, 7), dpi=300)

# Coordinates: Impact (x), Internal Control (y), Frequency (size)
# R1: Impact 5, Control 5, Freq 5 -> IC 15
# R2: Impact 4, Control 5, Freq 5 -> IC 14
# R3: Impact 3, Control 5, Freq 4 -> IC 12
# R4: Impact 5, Control 1, Freq 5 -> IC 11

points = [
    {"id": "R1: Bucle de Edición de Video", "x": 5.0, "y": 5.0, "s": 1500, "color": "#d9534f", "ic": "IC=15/15", "prio": "Prioridad 1"},
    {"id": "R2: Ineficiencia en Ideación/Brief", "x": 4.0, "y": 5.0, "s": 1300, "color": "#f0ad4e", "ic": "IC=14/15", "prio": "Prioridad 2"},
    {"id": "R3: Adaptación Manual Publicación", "x": 3.0, "y": 5.0, "s": 1000, "color": "#337ab7", "ic": "IC=12/15", "prio": "Prioridad 3"},
    {"id": "R4: Espera por Aprobación Cliente", "x": 5.0, "y": 1.0, "s": 1400, "color": "#777777", "ic": "IC=11/15", "prio": "Excluido (Exógeno)"}
]

for p in points:
    ax.scatter(p["x"], p["y"], s=p["s"], color=p["color"], alpha=0.7, edgecolors='black', linewidth=1.5)
    offset_y = 0.25 if p["y"] > 2 else -0.35
    offset_x = -0.2 if p["x"] > 4 else 0.1
    ax.annotate(f'{p["id"]}\n[{p["ic"]} - {p["prio"]}]', 
                xy=(p["x"], p["y"]), 
                xytext=(p["x"] + offset_x, p["y"] + offset_y),
                fontweight='bold', fontsize=9,
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=p["color"], lw=1.5))

# Quadrants
ax.axvline(3.5, color='black', linestyle=':', lw=1.2)
ax.axhline(3.0, color='black', linestyle=':', lw=1.2)

ax.text(4.8, 4.8, 'CUADRANTE I: RESTRICCIONES CRÍTICAS\n(Alto Impacto, Alto Control Interno)\n--> Automatizar mediante MAS', 
        ha='right', va='top', fontsize=8, color='#d9534f', fontweight='bold', bbox=dict(boxstyle="square", fc="#ffebee", alpha=0.6))
ax.text(4.8, 1.3, 'CUADRANTE IV: RESTRICCIONES EXÓGENAS\n(Alto Impacto, Bajo Control Interno)\n--> Acuerdos de Nivel de Servicio (SLA)', 
        ha='right', va='bottom', fontsize=8, color='#555555', fontweight='bold', bbox=dict(boxstyle="square", fc="#f5f5f5", alpha=0.6))
ax.text(1.2, 4.8, 'CUADRANTE II: MEJORAS OPERATIVAS\n(Menor Impacto, Alto Control)', 
        ha='left', va='top', fontsize=8, color='#337ab7', fontweight='bold')

ax.set_xlim(1.0, 5.5)
ax.set_ylim(0.5, 5.5)
ax.set_xlabel('Magnitud del Impacto en Lead Time (1 a 5)')
ax.set_ylabel('Grado de Control Interno Organizacional (1 a 5)')
ax.set_title('Figura 8.1: Matriz Estratégica de Priorización de Restricciones Operativas (ToC)')
ax.grid(True, linestyle='--', alpha=0.4)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "fig_04_matriz_priorizacion.png"))
plt.close()

# 5. Stochastic Video Editing Curve
fig, ax = plt.subplots(figsize=(9, 5.5), dpi=300)

p_r1_values = np.linspace(0.0, 0.8, 100)
# TC_Real = TC_Base + P(R1)*TC_R1 + P(R2)*TC_R2
# TC_Base = 6h, TC_R1 = 2.5h, P(R2) = 0.30, TC_R2 = 1.5h
# Constant component = 6 + 0.30*1.5 = 6.45h
tc_real_values = 6.0 + p_r1_values * 2.5 + (0.30 * 1.5)

ax.plot(p_r1_values, tc_real_values, color='#2b5c8f', lw=2.5, label='Tiempo de Ciclo Esperado E[TC] (horas)')
ax.axhline(6.0, color='green', linestyle='--', label='Tiempo Base Óptimo (Happy Path: 6,0 h)')

# Current state point
p_current = 0.60
tc_current = 6.0 + 0.60 * 2.5 + 0.45 # 7.95
ax.scatter([p_current], [tc_current], color='#d9534f', s=120, zorder=5)
ax.annotate(f'Estado Actual As-Is:\nP(R1)=0.60 --> TC={tc_current:.2f} h\n(+32,5% retrabajo)',
            xy=(p_current, tc_current), xytext=(p_current - 0.22, tc_current + 0.4),
            arrowprops=dict(arrowstyle='->', color='#d9534f', lw=1.5),
            fontweight='bold', color='#d9534f', bbox=dict(boxstyle="round", fc="#ffebee", ec="#d9534f"))

# Target state point
p_target = 0.10
tc_target = 6.0 + 0.10 * 2.5 + 0.45 # 6.70
ax.scatter([p_target], [tc_target], color='#5cb85c', s=120, zorder=5)
ax.annotate(f'Estado Objetivo To-Be (con QC Agéntico):\nP(R1)=0.10 --> TC={tc_target:.2f} h\n(15,7% ahorro = 1.314 h/mes)',
            xy=(p_target, tc_target), xytext=(p_target + 0.05, tc_target - 0.6),
            arrowprops=dict(arrowstyle='->', color='#5cb85c', lw=1.5),
            fontweight='bold', color='#2e7d32', bbox=dict(boxstyle="round", fc="#e8f5e9", ec="#5cb85c"))

# Fill area between actual and target
ax.fill_between(p_r1_values, tc_target, tc_real_values, where=(p_r1_values >= p_target) & (p_r1_values <= p_current),
                color='#337ab7', alpha=0.15, label='Potencial de Reducción de Desperdicio NVA')

ax.set_xlabel('Probabilidad de Rechazo en Primer Control de Calidad P(R1)')
ax.set_ylabel('Tiempo de Ciclo Total de Edición (Horas por Reel)')
ax.set_title('Figura 9.1: Modelo Estocástico de Retrabajo en Edición de Video (Restricción R1)')
ax.legend(loc='upper left')
ax.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "fig_05_curva_edicion_retrabajo.png"))
plt.close()

# 6. Automation Index
fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
restrictions = ['R1: Edición Video\n(Pasos 7-8)', 'R2: Ideación/Brief\n(Pasos 1, 2, 5)', 'R3: Publicación\n(Pasos 9, 14-15)', 'R4: Espera Cliente\n(Paso 10)']
x_r = np.arange(len(restrictions))
w_r = 0.2

repetitividad = [5.0, 4.0, 5.0, 3.0]
determinismo = [5.0, 4.0, 5.0, 1.0]
api_disp = [5.0, 5.0, 5.0, 2.0]
ia_total = [5.0, 4.3, 5.0, 2.0]

ax.bar(x_r - 1.5*w_r, repetitividad, w_r, label='Repetitividad', color='#5bc0de')
ax.bar(x_r - 0.5*w_r, determinismo, w_r, label='Determinismo', color='#337ab7')
ax.bar(x_r + 0.5*w_r, api_disp, w_r, label='Disponibilidad API', color='#2b5c8f')
bars_ia = ax.bar(x_r + 1.5*w_r, ia_total, w_r, label='Índice Automatización (IA)', color='#d9534f')

ax.axhline(4.0, color='red', linestyle='--', label='Umbral Mínimo de Automatización (IA >= 4.0)')
ax.set_ylabel('Calificación (Escala 1 a 5)')
ax.set_title('Figura 10.1: Evaluación de Factibilidad Técnica mediante Índice de Automatización (IA)')
ax.set_xticks(x_r)
ax.set_xticklabels(restrictions)
ax.set_ylim(0, 5.8)
ax.legend(loc='lower left', ncol=2, fontsize=8)
ax.grid(True, linestyle='--', alpha=0.5)

for i, ia in enumerate(ia_total):
    status = "INCLUIDO" if ia >= 4.0 else "EXCLUIDO"
    col = "#2e7d32" if ia >= 4.0 else "#c62828"
    ax.text(i + 1.5*w_r, ia + 0.15, f'{ia:.1f}\n({status})', ha='center', va='bottom', fontsize=8, fontweight='bold', color=col)

plt.tight_layout()
plt.savefig(os.path.join(output_dir, "fig_06_indice_automatizacion.png"))
plt.close()

# 7. VSM Comparison As-Is vs To-Be
fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
fases = ['Macrociclo I\nIdeación', 'Macrociclo II\nPreproducción', 'Macrociclo III\nEdición', 'Macrociclo IV\nAprobación/Publ.', 'Lead Time Total\n(Promedio/pza)']
as_is_prom = [19.03, 27.40, 26.56, 19.55, 92.54 + 30.58]
to_be_prom = [2.00, 22.00, 20.00, 15.00, 59.00] # Projections with MAS

x_f = np.arange(len(fases))
w_f = 0.35

rects_as_is = ax.bar(x_f - w_f/2, as_is_prom, w_f, label='Estado Actual (As-Is) [h/pza]', color='#d9534f', alpha=0.85, edgecolor='black')
rects_to_be = ax.bar(x_f + w_f/2, to_be_prom, w_f, label='Estado Futuro (To-Be con MAS) [h/pza]', color='#5cb85c', alpha=0.85, edgecolor='black')

ax.set_ylabel('Horas Promedio por Pieza')
ax.set_title('Figura 11.1: Comparativa de Tiempos de Ciclo y Lead Time: As-Is vs To-Be')
ax.set_xticks(x_f)
ax.set_xticklabels(fases)
ax.legend()
ax.grid(True, linestyle='--', alpha=0.5)

# Annotate reduction on Lead Time
ax.annotate('-52,1% Lead Time\n(Eliminación NVA)', 
            xy=(4, 59.00), xytext=(4, 85.00),
            ha='center', fontweight='bold', color='#2e7d32',
            arrowprops=dict(arrowstyle='->', color='#2e7d32', lw=1.5))

plt.tight_layout()
plt.savefig(os.path.join(output_dir, "fig_07_vsm_comparacion_as_is_to_be.png"))
plt.close()

print("Todas las gráficas analíticas han sido generadas exitosamente en:", output_dir)
