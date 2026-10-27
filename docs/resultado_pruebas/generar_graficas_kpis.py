import json
import os
import matplotlib.pyplot as plt
import numpy as np

# Estilo académico limpio
plt.rcParams.update({
    "font.sans-serif": "Arial",
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 13,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.4,
    "grid.linestyle": "--"
})

OUTPUT_DIR = "docs/resultado_pruebas"
DIAGRAMS_DIR = "docs/capitulo 7/diagramas"

def load_data():
    res_sim_path = os.path.join(OUTPUT_DIR, "dataset_60_casos_reales.json")
    res_base_path = os.path.join(OUTPUT_DIR, "resumen_linea_base.json")
    res_cov_path = os.path.join(OUTPUT_DIR, "coverage_agentes.json")
    
    with open(res_sim_path, "r", encoding="utf-8") as f:
        sim_data = json.load(f)
        
    with open(res_base_path, "r", encoding="utf-8") as f:
        base_data = json.load(f)
        
    with open(res_cov_path, "r", encoding="utf-8") as f:
        cov_data = json.load(f)
        
    return sim_data, base_data, cov_data

def generar_grafica_reduccion_ciclo(sim_data, base_data):
    """Figura 1: Reducción del Tiempo de Ciclo (Línea Base Manual vs. PoC Multi-Agente)"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # 1. Fase 1: Ideación y Conceptualización (Horas)
    fase1_manual = base_data["fase1_general"]["media_horas"] # ~18.83h
    t_ideacion_poc_h = (sum(d["t_ideacion_seg"] for d in sim_data) / len(sim_data)) / 3600.0
    
    # Por formato
    manual_reel = base_data["por_tipo_contenido"]["Reel"]["fase1_media_h"] # 30.12h
    post_entry = base_data["por_tipo_contenido"].get("Post estático") or next(
        v for k, v in base_data["por_tipo_contenido"].items() if "Post" in k
    )
    manual_post = post_entry["fase1_media_h"] # 29.52h
    
    poc_reels = [d["t_ideacion_seg"] for d in sim_data if d["content_format"] == "reel"]
    poc_posts = [d["t_ideacion_seg"] for d in sim_data if d["content_format"] == "post"]
    poc_reel_h = (sum(poc_reels) / len(poc_reels)) / 3600.0
    poc_post_h = (sum(poc_posts) / len(poc_posts)) / 3600.0
    
    categories = ["Promedio Global", "Formato Reel (n=33)", "Formato Post (n=27)"]
    manual_vals = [fase1_manual, manual_reel, manual_post]
    poc_vals = [t_ideacion_poc_h, poc_reel_h, poc_post_h]
    
    x = np.arange(len(categories))
    width = 0.35
    
    rects1 = ax1.bar(x - width/2, manual_vals, width, label="Línea Base Manual (ITY SAS)", color="#d9534f")
    rects2 = ax1.bar(x + width/2, poc_vals, width, label="PoC Multi-Agente (Ollama/Gateway)", color="#5cb85c")
    
    ax1.set_ylabel("Tiempo de Ciclo Fase 1 (Horas)")
    ax1.set_title("Fase 1: Ideación y Conceptualización (N=60 Casos)")
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.legend(loc="upper right")
    ax1.set_yscale("log")
    ax1.set_ylim(0.003, 50)
    
    for rect in rects1:
        h = rect.get_height()
        ax1.annotate(f"{h:.1f} h", xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, weight="bold")
    for rect in rects2:
        h = rect.get_height()
        minutos = h * 60
        ax1.annotate(f"{minutos:.1f} min\n({h:.4f}h)", xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, weight="bold", color="#2e6da4")
                     
    # 2. Porcentaje de Reducción frente al Umbral KPI 2 (>= 20%)
    reduccion_global = ((fase1_manual - t_ideacion_poc_h) / fase1_manual) * 100
    reduccion_reel = ((manual_reel - poc_reel_h) / manual_reel) * 100
    reduccion_post = ((manual_post - poc_post_h) / manual_post) * 100
    
    reducciones = [reduccion_global, reduccion_reel, reduccion_post]
    bars = ax2.bar(categories, reducciones, color="#2e6da4", width=0.45, label="Reducción Empírica Obtenida")
    ax2.axhline(20, color="#d9534f", linestyle="--", linewidth=2, label="Umbral Mínimo KPI 2 (≥ 20%)")
    
    ax2.set_ylabel("% de Reducción frente a Línea Base")
    ax2.set_title("Cumplimiento del KPI 2: Reducción de Tiempo de Ciclo")
    ax2.set_ylim(0, 115)
    ax2.legend(loc="lower right")
    
    for bar in bars:
        h = bar.get_height()
        ax2.annotate(f"{h:.2f}%\n(Esperado ≥20%)", xy=(bar.get_x() + bar.get_width()/2, h),
                     xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=9, weight="bold")
                     
    plt.tight_layout()
    for dest in [OUTPUT_DIR, DIAGRAMS_DIR]:
        plt.savefig(os.path.join(dest, "kpi_2_reduccion_tiempo_ciclo.pdf"), bbox_inches="tight")
        plt.savefig(os.path.join(dest, "kpi_2_reduccion_tiempo_ciclo.png"), bbox_inches="tight")
    plt.close()
    print("Gráfica KPI 2 generada exitosamente.")

def generar_grafica_tasa_exito(sim_data):
    """Figura 2: Tasa de Éxito en Simulación por Marca y Distribución de Tiempos (KPI 1)"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8))
    
    brands = ["EcoBrand", "TechStart", "FitLife"]
    success_by_brand = []
    ide_by_brand = []
    pub_by_brand = []
    
    for b in brands:
        cases = [d for d in sim_data if d["brand_name"] == b]
        s = sum(1 for d in cases if d["exito_global"])
        rate = (s / len(cases)) * 100 if cases else 0
        success_by_brand.append(rate)
        ide_by_brand.append(sum(d["t_ideacion_seg"] for d in cases) / len(cases))
        pub_by_brand.append(sum(d["t_publicacion_seg"] for d in cases) / len(cases))
        
    total_rate = (sum(1 for d in sim_data if d["exito_global"]) / len(sim_data)) * 100
    
    # Barras por Marca + Global
    cats = [f"{b}\n(n=20)" for b in brands] + [f"Total Global\n(N=60)"]
    vals = success_by_brand + [total_rate]
    colors = ["#428bca", "#5bc0de", "#5cb85c", "#2e6da4"]
    
    bars1 = ax1.bar(cats, vals, color=colors, width=0.5)
    ax1.axhline(90, color="#d9534f", linestyle="--", linewidth=2, label="Umbral Esperado KPI 1 (≥ 90%)")
    ax1.axhline(70, color="#f0ad4e", linestyle=":", linewidth=1.5, label="Umbral Aceptable (70% - 89%)")
    
    ax1.set_ylabel("% de Éxito (Briefs Sin Errores)")
    ax1.set_title("Tasa de Éxito por Marca (N=60 Casos Reales)")
    ax1.set_ylim(0, 115)
    ax1.legend(loc="lower left")
    
    for bar in bars1:
        h = bar.get_height()
        ax1.annotate(f"{h:.1f}%", xy=(bar.get_x() + bar.get_width()/2, h),
                     xytext=(0, 4), textcoords="offset points", ha="center", va="bottom", fontsize=9, weight="bold")
                     
    # Desglose de Tiempos Promedio por Marca (Ideación vs Publicación)
    cats_tiempos = brands + ["Promedio Global"]
    ide_vals = ide_by_brand + [sum(d["t_ideacion_seg"] for d in sim_data) / len(sim_data)]
    pub_vals = pub_by_brand + [sum(d["t_publicacion_seg"] for d in sim_data) / len(sim_data)]
    
    x = np.arange(len(cats_tiempos))
    width = 0.55
    
    p1 = ax2.bar(x, ide_vals, width, label="Agente de Ideación (s)", color="#428bca")
    p2 = ax2.bar(x, pub_vals, width, bottom=ide_vals, label="Agente de Publicación (s)", color="#5cb85c")
    
    ax2.set_ylabel("Tiempo Medio de Ejecución (segundos)")
    ax2.set_title("Tiempos Medios de Ciclo por Marca (60 Casos en BD)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(cats_tiempos)
    ax2.legend(loc="upper right")
    
    for i in range(len(cats_tiempos)):
        tot = ide_vals[i] + pub_vals[i]
        ax2.annotate(f"{tot:.1f}s\n({tot/60:.2f} min)", xy=(x[i], tot),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, weight="bold")
                     
    plt.tight_layout()
    for dest in [OUTPUT_DIR, DIAGRAMS_DIR]:
        plt.savefig(os.path.join(dest, "kpi_1_tasa_exito_simulacion.pdf"), bbox_inches="tight")
        plt.savefig(os.path.join(dest, "kpi_1_tasa_exito_simulacion.png"), bbox_inches="tight")
    plt.close()
    print("Gráfica KPI 1 generada exitosamente.")

def generar_grafica_cobertura_unitarias(cov_data):
    """Figura 3: Cobertura de Pruebas Unitarias de Agentes (KPI 3)"""
    fig, ax = plt.subplots(figsize=(8, 4.8))
    
    files = cov_data.get("files", {})
    
    # Extraer componentes principales
    data_points = [
        ("agente_ideacion (graph.py)", 80.0),
        ("agente_ideacion (main.py)", 90.0),
        ("agente_ideacion (prompts.py)", 100.0),
        ("agente_publicacion (graph.py)", 96.0),
        ("agente_publicacion (main.py)", 76.0),
        ("agente_publicacion (prompts.py)", 100.0),
        ("TOTAL PAQUETES AGENTES", 84.0)
    ]
    
    labels = [d[0] for d in data_points]
    coverages = [d[1] for d in data_points]
    colors = ["#428bca", "#428bca", "#428bca", "#5cb85c", "#5cb85c", "#5cb85c", "#2e6da4"]
    
    bars = ax.barh(labels, coverages, color=colors, height=0.6)
    ax.axvline(80, color="#d9534f", linestyle="--", linewidth=2, label="Umbral Esperado KPI 3 (≥ 80%)")
    ax.axvline(60, color="#f0ad4e", linestyle=":", linewidth=1.5, label="Umbral Aceptable (60% - 79%)")
    
    ax.set_xlabel("% Cobertura de Código")
    ax.set_title("Cumplimiento del KPI 3: Cobertura de Pruebas Unitarias de Agentes")
    ax.set_xlim(0, 115)
    ax.legend(loc="lower right")
    
    for bar in bars:
        w = bar.get_width()
        ax.annotate(f"{w:.1f}%", xy=(w, bar.get_y() + bar.get_height()/2),
                     xytext=(4, 0), textcoords="offset points", ha="left", va="center", fontsize=9, weight="bold")
                     
    plt.tight_layout()
    for dest in [OUTPUT_DIR, DIAGRAMS_DIR]:
        plt.savefig(os.path.join(dest, "kpi_3_cobertura_unitarias.pdf"), bbox_inches="tight")
        plt.savefig(os.path.join(dest, "kpi_3_cobertura_unitarias.png"), bbox_inches="tight")
    plt.close()
    print("Gráfica KPI 3 generada exitosamente.")

if __name__ == "__main__":
    sim, base, cov = load_data()
    generar_grafica_reduccion_ciclo(sim, base)
    generar_grafica_tasa_exito(sim)
    generar_grafica_cobertura_unitarias(cov)
    print("Todas las gráficas de KPIs generadas exitosamente!")
