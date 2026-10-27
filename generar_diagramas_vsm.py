import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

output_dir = "docs/documento_diagnostico/graficas"
os.makedirs(output_dir, exist_ok=True)

# 1. Diagrama de Flujo 16 Pasos (AS-IS)
fig, ax = plt.subplots(figsize=(14, 10), dpi=300)
ax.set_xlim(0, 14)
ax.set_ylim(0, 18)
ax.axis('off')

# Macrocycles background boxes
# I: Ideación (y: 13.5 to 17.5)
p1 = patches.Rectangle((0.5, 13.5), 13, 3.8, linewidth=1.5, edgecolor='#2b5c8f', facecolor='#e8f0fe', alpha=0.5, linestyle='--')
ax.add_patch(p1)
ax.text(0.8, 16.8, "MACROCICLO I: IDEACIÓN Y ESTRATEGIA (Pasos 1, 2, 5)", fontsize=11, fontweight='bold', color='#1a365d')

# II: Preproducción (y: 9.2 to 13.0)
p2 = patches.Rectangle((0.5, 9.2), 13, 3.8, linewidth=1.5, edgecolor='#4682b4', facecolor='#f0f7ff', alpha=0.5, linestyle='--')
ax.add_patch(p2)
ax.text(0.8, 12.5, "MACROCICLO II: PREPRODUCCIÓN Y FABRICACIÓN (Pasos 3, 4, 6)", fontsize=11, fontweight='bold', color='#1f497d')

# III: Edición y Calidad (y: 4.8 to 8.8)
p3 = patches.Rectangle((0.5, 4.8), 13, 3.8, linewidth=1.5, edgecolor='#d9534f', facecolor='#fdf2e9', alpha=0.5, linestyle='--')
ax.add_patch(p3)
ax.text(0.8, 8.2, "MACROCICLO III: EDICIÓN Y CONTROL DE CALIDAD (Pasos 7, 8, 9) [RESTRICCIÓN R1]", fontsize=11, fontweight='bold', color='#990000')

# IV: Aprobación y Publicación (y: 0.5 to 4.4)
p4 = patches.Rectangle((0.5, 0.5), 13, 3.8, linewidth=1.5, edgecolor='#5cb85c', facecolor='#eafaf1', alpha=0.5, linestyle='--')
ax.add_patch(p4)
ax.text(0.8, 3.9, "MACROCICLO IV: APROBACIÓN Y PUBLICACIÓN (Pasos 10-16) [RESTRICCIÓN R3 / R4]", fontsize=11, fontweight='bold', color='#145a32')

# Helper to draw boxes
def draw_box(x, y, w, h, text, color='#ffffff', border='#333333', shape='rect'):
    if shape == 'diamond':
        poly = patches.Polygon([[x+w/2, y], [x+w, y+h/2], [x+w/2, y+h], [x, y+h/2]], 
                               closed=True, facecolor=color, edgecolor=border, lw=1.2)
        ax.add_patch(poly)
    else:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1", 
                                      facecolor=color, edgecolor=border, lw=1.2)
        ax.add_patch(rect)
    ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=8, fontweight='bold', multialignment='center')

# Draw 16 steps
# Macro I
draw_box(1.0, 14.2, 3.2, 1.8, "Paso 1: Recepción Brief\ny Análisis de Cuenta\n(CM / WhatsApp)", '#ffffff', '#2b5c8f')
draw_box(5.0, 14.2, 3.2, 1.8, "Paso 2: Decisión Formato\ny Búsqueda Tendencias\n(Manual / Feed)", '#ffffff', '#2b5c8f')
draw_box(9.2, 14.2, 3.2, 1.8, "Paso 5: Documentación\nde Referentes\n(Excel no reutilizable)", '#ffffff', '#2b5c8f')

# Macro II
draw_box(1.0, 9.8, 3.2, 1.8, "Paso 3: Planificación\nVisita y Guionaje\n(Sin plantilla fija)", '#ffffff', '#4682b4')
draw_box(5.0, 9.8, 3.2, 1.8, "Paso 4: Grabación\ncon Material Existente", '#ffffff', '#4682b4')
draw_box(9.2, 9.8, 3.2, 1.8, "Paso 6: Grabación\nen Locación\n(Logística / Esperas)", '#ffffff', '#4682b4')

# Macro III
draw_box(1.0, 5.4, 3.2, 1.8, "Paso 7: Edición Base\n(Rough Cut + Subtítulos)\n[C/T base = 6h]", '#ffffff', '#d9534f')
draw_box(5.0, 5.4, 3.2, 1.8, "Paso 8: Control Calidad\nInterno (Revisión)\n[P(R1)=0.60 | P(R2)=0.30]", '#ffdddd', '#d9534f', shape='diamond')
draw_box(9.2, 5.4, 3.2, 1.8, "Paso 9: Integración a\nParrilla y Redacción Copys\n(Manual por red)", '#ffffff', '#d9534f')

# Macro IV
draw_box(1.0, 1.1, 2.5, 1.8, "Paso 10: Presentación\ny Espera Aprobación\n[L/T = 19,15 h]", '#fff3cd', '#f0ad4e')
draw_box(4.0, 1.1, 2.5, 1.8, "Paso 11-12: Aprobación\ny Verificación Accesos", '#ffffff', '#5cb85c')
draw_box(7.0, 1.1, 2.5, 1.8, "Paso 13-14: Ajustes de\nÚltima Milla y Formatos", '#ffffff', '#5cb85c')
draw_box(10.0, 1.1, 2.5, 1.8, "Paso 15-16: Publicación\nManual en Redes\n[Retraso = 0,40 h]", '#ffffff', '#5cb85c')

# Connect arrows
def draw_arrow(x1, y1, x2, y2, label=""):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="->", color="#333333", lw=1.5))
    if label:
        ax.text((x1+x2)/2, (y1+y2)/2 + 0.15, label, fontsize=7, ha='center', backgroundcolor='#ffffff')

# Flow arrows
draw_arrow(4.2, 15.1, 5.0, 15.1)
draw_arrow(8.2, 15.1, 9.2, 15.1)
draw_arrow(10.8, 14.2, 10.8, 12.0)
draw_arrow(10.8, 12.0, 2.6, 12.0)
draw_arrow(2.6, 12.0, 2.6, 11.6)

draw_arrow(4.2, 10.7, 5.0, 10.7)
draw_arrow(8.2, 10.7, 9.2, 10.7)
draw_arrow(10.8, 9.8, 10.8, 7.8)
draw_arrow(10.8, 7.8, 2.6, 7.8)
draw_arrow(2.6, 7.8, 2.6, 7.2)

draw_arrow(4.2, 6.3, 5.0, 6.3)
draw_arrow(8.2, 6.3, 9.2, 6.3, "Aprobado (40%)")
# Feedback loop
ax.annotate("Rechazado (60%)\nBucle Retrabajo", xy=(2.6, 7.2), xytext=(6.6, 7.4),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.3", color="#d9534f", lw=1.8),
            color="#d9534f", fontweight='bold', fontsize=8, ha='center')

draw_arrow(10.8, 5.4, 10.8, 3.4)
draw_arrow(10.8, 3.4, 2.2, 3.4)
draw_arrow(2.2, 3.4, 2.2, 2.9)

draw_arrow(3.5, 2.0, 4.0, 2.0)
draw_arrow(6.5, 2.0, 7.0, 2.0)
draw_arrow(9.5, 2.0, 10.0, 2.0)

ax.set_title('Figura 3.1: Diagrama de Flujo As-Is de los 16 Pasos y 4 Macrociclos en ITY SAS', fontsize=13, pad=15)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "fig_08_diagrama_flujo_16_pasos.png"))
plt.close()

# 2. VSM Macro Diagram (AS-IS)
fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
ax.set_xlim(0, 16)
ax.set_ylim(0, 10)
ax.axis('off')

# Title
ax.text(8, 9.5, "VALUE STREAM MAPPING (VSM) AGREGADO - ESTADO ACTUAL (AS-IS)\nMuestra Global N=315 Piezas | Agencia ITY SAS (Agosto 2026)", 
        ha='center', va='center', fontsize=12, fontweight='bold', color='#1a365d')

# Customers & Agency Box
draw_box(1.0, 7.2, 3.0, 1.5, "CLIENTES (10 Cuentas)\nDemanda: 315 piezas/mes\nFrecuencia: 20-30 pubs/mes", '#e3f2fd', '#1565c0')
draw_box(12.0, 7.2, 3.0, 1.5, "AUDIENCIA / PLATAFORMAS\nMeta, TikTok, LinkedIn\nSaturación Algorítmica", '#e3f2fd', '#1565c0')
draw_box(6.5, 7.2, 3.0, 1.5, "CONTROL DE PRODUCCIÓN\nCoordinación por WhatsApp\nTablero Trello Manual", '#fff8e1', '#f57f17')

# Information Flow Arrows
ax.annotate("Briefs (WhatsApp/Correo)\nInformación Incompleta", xy=(6.5, 7.9), xytext=(4.0, 7.9),
            arrowprops=dict(arrowstyle="->", color="#1565c0", lw=1.5, linestyle='--'), fontsize=7, ha='center')
ax.annotate("Parrilla para Aprobación\nEspera Media: 19,15 h", xy=(6.5, 7.4), xytext=(4.0, 7.4),
            arrowprops=dict(arrowstyle="<-", color="#e65100", lw=1.5, linestyle='--'), fontsize=7, ha='center')
ax.annotate("Publicación Manual / API\nRetraso: 0,40 h/pza", xy=(12.0, 7.9), xytext=(9.5, 7.9),
            arrowprops=dict(arrowstyle="->", color="#1565c0", lw=1.5, linestyle='--'), fontsize=7, ha='center')

# Process Boxes
boxes_vsm = [
    {"name": "I. IDEACIÓN Y ESTRATEGIA\n(Pasos 1, 2 y 5)", "x": 0.8, "ct": "C/T = 19,03 h", "tt": "T/T = 5.994,93 h", "wip": "WIP = 10 briefs", "oper": "1 CM / Cuenta"},
    {"name": "II. PREPRODUCCIÓN\n(Pasos 3, 4 y 6)", "x": 4.5, "ct": "C/T = 27,40 h", "tt": "T/T = 8.630,51 h", "wip": "WIP = 15 piezas", "oper": "1 Diseñador"},
    {"name": "III. EDICIÓN Y CALIDAD\n(Pasos 7, 8 y 9)", "x": 8.2, "ct": "C/T = 134,94 h (*Reels)", "tt": "T/T = 8.366,19 h", "wip": "WIP = 25 videos", "oper": "1 Editor (Cuello)"},
    {"name": "IV. APROBACIÓN & PUBL.\n(Pasos 10 a 16)", "x": 11.9, "ct": "C/T = 19,55 h", "tt": "T/T = 6.158,60 h", "wip": "WIP = 40 piezas", "oper": "CM + Cliente"}
]

for b in boxes_vsm:
    draw_box(b["x"], 3.5, 3.2, 2.5, 
             f"{b['name']}\n------------------\n{b['oper']}\n{b['ct']}\n{b['tt']}\n{b['wip']}",
             '#ffffff', '#333333')

# Inventory Triangles (WIP between phases)
def draw_inventory(x, y, text):
    poly = patches.Polygon([[x, y], [x+0.5, y+0.8], [x-0.5, y+0.8]], closed=True, facecolor='#fff9c4', edgecolor='#fbc02d', lw=1.2)
    ax.add_patch(poly)
    ax.text(x, y+0.35, "I", ha='center', va='center', fontweight='bold', fontsize=8)
    ax.text(x, y-0.3, text, ha='center', va='top', fontsize=7, fontweight='bold', color='#f57f17')

draw_inventory(4.2, 4.3, "Espera Brief\n1.200 h")
draw_inventory(7.9, 4.3, "Espera Logística\n2.400 h")
draw_inventory(11.6, 4.3, "Espera Cliente\n6.032,97 h")

# Flow Arrows between process boxes
draw_arrow(4.0, 4.75, 4.5, 4.75)
draw_arrow(7.7, 4.75, 8.2, 4.75)
draw_arrow(11.4, 4.75, 11.9, 4.75)

# Stepline (Timeline at the bottom)
y_line = 1.2
ax.plot([0.8, 15.1], [y_line, y_line], color='black', lw=1.5)

# Draw stairs: Low = C/T (VA), High = Wait (NVA)
stairs = [
    # (x_start, x_end, is_nva, label, hours)
    (0.8, 4.0, False, "VA: 19,03 h", 19.03),
    (4.0, 4.5, True, "NVA: 3,81 h", 3.81),
    (4.5, 7.7, False, "VA: 27,40 h", 27.40),
    (7.7, 8.2, True, "NVA: 7,62 h", 7.62),
    (8.2, 11.4, False, "VA: 26,56 h", 26.56),
    (11.4, 11.9, True, "NVA: 19,15 h", 19.15),
    (11.9, 15.1, False, "VA: 19,55 h", 19.55)
]

for s_start, s_end, is_nva, lbl, val in stairs:
    h_level = y_line + 0.6 if is_nva else y_line - 0.5
    ax.plot([s_start, s_end], [h_level, h_level], color='#d9534f' if is_nva else '#2e7d32', lw=2)
    ax.plot([s_start, s_start], [y_line, h_level], color='gray', lw=1, linestyle=':')
    ax.plot([s_end, s_end], [y_line, h_level], color='gray', lw=1, linestyle=':')
    ax.text((s_start+s_end)/2, h_level + (0.15 if is_nva else -0.3), lbl, ha='center', fontsize=7, 
            fontweight='bold', color='#d9534f' if is_nva else '#2e7d32')

# Total metrics box
draw_box(0.8, 0.1, 14.3, 0.8, 
         "TOTAL LEAD TIME (L/T): 38.783,20 h (123,12 h/pieza) | VALOR AGREGADO (VA): 29.150,23 h (92,54 h/pza) | NO VALOR AGREGADO (NVA): 9.632,97 h | EFICIENCIA (PCE): 75,16%",
         '#e8f5e9', '#2e7d32')

plt.tight_layout()
plt.savefig(os.path.join(output_dir, "fig_09_vsm_macro_diagram.png"))
plt.close()

# 3. Ishikawa Diagram (Cuellos de botella)
fig, ax = plt.subplots(figsize=(12, 7), dpi=300)
ax.set_xlim(0, 12)
ax.set_ylim(0, 8)
ax.axis('off')

# Spine
ax.plot([1.5, 9.8], [4.0, 4.0], color='#1a365d', lw=4)
# Head
head = patches.Polygon([[9.8, 4.0], [11.8, 4.0], [11.8, 3.0], [9.8, 4.0]], closed=True, facecolor='#d9534f', edgecolor='black')
draw_box(9.8, 3.0, 2.0, 2.0, "BAJA FRECUENCIA\nDE PUBLICACIÓN\nY SOBRECARGA\nOPERATIVA EN\nITY SAS", '#ffebee', '#d9534f')

# Bones
# Top bones: Mano de Obra, Métodos, Mediciones
ax.plot([3.0, 4.2], [6.5, 4.0], color='#1a365d', lw=2.5)
ax.text(3.0, 6.7, "MANO DE OBRA (PERSONAS)", fontsize=9, fontweight='bold', color='#1a365d')
ax.text(2.6, 5.8, "• Burnout creativo (79%)\n• Falta de especialistas\n• Sobrecarga cognitiva", fontsize=7.5)

ax.plot([5.5, 6.7], [6.5, 4.0], color='#1a365d', lw=2.5)
ax.text(5.5, 6.7, "MÉTODOS Y PROCESOS", fontsize=9, fontweight='bold', color='#1a365d')
ax.text(5.1, 5.8, "• Flujo secuencial rígido\n• Aprobaciones manuales\n• Falta de checklists QC", fontsize=7.5)

ax.plot([8.0, 8.8], [6.5, 4.0], color='#1a365d', lw=2.5)
ax.text(8.0, 6.7, "MEDICIÓN Y CONTROL", fontsize=9, fontweight='bold', color='#1a365d')
ax.text(7.6, 5.8, "• Tiempos en Excel ad-hoc\n• Métricas de vanidad\n• Sin auditoría de retrabajo", fontsize=7.5)

# Bottom bones: Máquinas/Tecnología, Materiales/Briefs, Entorno
ax.plot([3.0, 4.2], [1.5, 4.0], color='#1a365d', lw=2.5)
ax.text(3.0, 1.2, "HERRAMIENTAS / TECNOLOGÍA", fontsize=9, fontweight='bold', color='#1a365d')
ax.text(2.6, 2.0, "• Silos: Canva, Drive, Meta\n• Sin orquestación agéntica\n• Publicación no centralizada", fontsize=7.5)

ax.plot([5.5, 6.7], [1.5, 4.0], color='#1a365d', lw=2.5)
ax.text(5.5, 1.2, "MATERIALES (BRIEFS & ASSETS)", fontsize=9, fontweight='bold', color='#1a365d')
ax.text(5.1, 2.0, "• Briefs incompletos (60%)\n• Referentes sin estandarizar\n• Feedback caótico en WhatsApp", fontsize=7.5)

ax.plot([8.0, 8.8], [1.5, 4.0], color='#1a365d', lw=2.5)
ax.text(8.0, 1.2, "ENTORNO / ALGORITMOS", fontsize=9, fontweight='bold', color='#1a365d')
ax.text(7.6, 2.0, "• Saturación algorítmica\n• Presión 20-30 pubs/mes\n• Fatiga publicitaria 35-40 d", fontsize=7.5)

ax.set_title('Figura 8.2: Diagrama de Causa y Efecto (Ishikawa 6M) de las Ineficiencias en ITY SAS', fontsize=12, pad=15)
plt.tight_layout()
plt.savefig(os.path.join(output_dir, "fig_11_ishikawa_cuellos_botella.png"))
plt.close()

# 4. VSM Microprocess Video Editing
fig, ax = plt.subplots(figsize=(13, 6), dpi=300)
ax.set_xlim(0, 14)
ax.set_ylim(0, 7)
ax.axis('off')

ax.text(7, 6.5, "MICRO-VSM: SUBPROCESO DE EDICIÓN DE VIDEO (RESTRICCIÓN R1)\nDesagregación del Bucle de Retrabajo Interno en Reels (N=62 piezas)",
        ha='center', va='center', fontsize=11, fontweight='bold', color='#990000')

draw_box(0.5, 3.0, 2.5, 2.0, "Ingreso de Material\nCrudo y Guion\n(Paso 6)", '#ffffff', '#333333')
draw_box(3.5, 3.0, 2.5, 2.0, "Edición Base:\nRough Cut + Ritmo\n(C/T base = 2,0 h)", '#ffffff', '#2b5c8f')
draw_box(6.5, 3.0, 2.5, 2.0, "Subtitulado,\nAudio y Color LUT\n(C/T base = 4,0 h)", '#ffffff', '#2b5c8f')
draw_box(9.5, 3.0, 2.0, 2.0, "QC Interno:\n¿Aprobado?\n[P(R1)=0.60]", '#ffdddd', '#d9534f', shape='diamond')
draw_box(12.0, 3.0, 1.8, 2.0, "Entrega a\nParrilla\n(Paso 9)", '#e8f5e9', '#2e7d32')

# Arrows
draw_arrow(3.0, 4.0, 3.5, 4.0)
draw_arrow(6.0, 4.0, 6.5, 4.0)
draw_arrow(9.0, 4.0, 9.5, 4.0)
draw_arrow(11.5, 4.0, 12.0, 4.0, "Sí (40%)")

# Feedback 1
ax.annotate("Rechazo Ronda 1 (60%)\nC/T_R1 = 2,5 h (Subtítulos, Ritmo)", xy=(5.0, 5.0), xytext=(10.5, 5.6),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.3", color="#d9534f", lw=2),
            color="#d9534f", fontweight='bold', fontsize=8, ha='center')

# Feedback 2
ax.annotate("Rechazo Ronda 2 (30%)\nC/T_R2 = 1,5 h (Ajustes Menores)", xy=(8.0, 2.8), xytext=(10.5, 1.8),
            arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.3", color="#f0ad4e", lw=1.8),
            color="#e65100", fontweight='bold', fontsize=8, ha='center')

draw_box(0.5, 0.5, 13.0, 0.9, 
         "ECUACIÓN: TC_Real = TC_Base + P(R1)*TC_R1 + P(R2)*TC_R2 = 6,0 + (0,60*2,5) + (0,30*1,5) = 7,95 h (+32,5% Retrabajo)\nImpacto en 62 reels: 8.366,19 horas totales acumuladas | Horas de desperdicio evitable: 2.366,19 h/mes",
         '#ffebee', '#d9534f')

plt.tight_layout()
plt.savefig(os.path.join(output_dir, "fig_10_vsm_micro_edicion.png"))
plt.close()

print("Diagramas de proceso VSM e Ishikawa generados exitosamente.")
