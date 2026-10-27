import pandas as pd
import numpy as np
import json

def analyze_baseline():
    csv_path = "docs/resultado_pruebas/linea_base_manual_ity_sas.csv"
    df = pd.read_csv(csv_path)
    
    # Identify key time columns
    col_fase1 = "Tiempo de ciclo Fase 1 (h)"
    col_espera = "Tiempo de espera antes de Fase 2 (h)"
    col_diseno = "Tiempo de ciclo Diseo (h)" if "Tiempo de ciclo Diseo (h)" in df.columns else [c for c in df.columns if "Dise" in c and "ciclo" in c][0]
    col_edicion = "Tiempo de ciclo Pre/Edicin (h)" if "Tiempo de ciclo Pre/Edicin (h)" in df.columns else [c for c in df.columns if "Edici" in c and "ciclo" in c][0]
    col_espera_aprob = "Tiempo espera aprobacin cliente (h)" if "Tiempo espera aprobacin cliente (h)" in df.columns else [c for c in df.columns if "aprobaci" in c and "espera" in c][0]
    col_retraso = "Retraso en publicacin (h)" if "Retraso en publicacin (h)" in df.columns else [c for c in df.columns if "Retraso" in c][0]
    
    # Ensure numeric
    for col in [col_fase1, col_espera, col_diseno, col_edicion, col_espera_aprob, col_retraso]:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
    df['Tiempo_Produccion_Fase2'] = df[col_diseno] + df[col_edicion]
    df['Tiempo_Ciclo_Total'] = df[col_fase1] + df[col_espera] + df['Tiempo_Produccion_Fase2'] + df[col_espera_aprob] + df[col_retraso]
    
    summary = {
        "total_muestras": int(len(df)),
        "cuentas_analizadas": df['Cuenta / Cliente'].nunique(),
        "lista_cuentas": df['Cuenta / Cliente'].unique().tolist(),
        "fase1_general": {
            "media_horas": round(float(df[col_fase1].mean()), 2),
            "mediana_horas": round(float(df[col_fase1].median()), 2),
            "desv_std_horas": round(float(df[col_fase1].std()), 2),
            "min_horas": round(float(df[col_fase1].min()), 2),
            "max_horas": round(float(df[col_fase1].max()), 2),
        },
        "espera_fase2_general": {
            "media_horas": round(float(df[col_espera].mean()), 2),
            "mediana_horas": round(float(df[col_espera].median()), 2),
            "min_horas": round(float(df[col_espera].min()), 2),
            "max_horas": round(float(df[col_espera].max()), 2),
        },
        "tiempo_ciclo_total_general": {
            "media_horas": round(float(df['Tiempo_Ciclo_Total'].mean()), 2),
            "mediana_horas": round(float(df['Tiempo_Ciclo_Total'].median()), 2),
            "min_horas": round(float(df['Tiempo_Ciclo_Total'].min()), 2),
            "max_horas": round(float(df['Tiempo_Ciclo_Total'].max()), 2),
        },
        "por_tipo_contenido": {}
    }
    
    for fmt, group in df.groupby('Tipo de Contenido'):
        summary["por_tipo_contenido"][fmt] = {
            "n": int(len(group)),
            "fase1_media_h": round(float(group[col_fase1].mean()), 2),
            "fase1_mediana_h": round(float(group[col_fase1].median()), 2),
            "fase1_min_h": round(float(group[col_fase1].min()), 2),
            "fase1_max_h": round(float(group[col_fase1].max()), 2),
            "espera_media_h": round(float(group[col_espera].mean()), 2),
            "total_media_h": round(float(group['Tiempo_Ciclo_Total'].mean()), 2),
            "total_mediana_h": round(float(group['Tiempo_Ciclo_Total'].median()), 2),
        }
        
    output_path = "docs/resultado_pruebas/resumen_linea_base.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        
    print(f"Resumen guardado exitosamente en {output_path}")
    print(f"Total muestras: {summary['total_muestras']}")
    print(f"Fase 1 (Ideación y Brief) promedio manual: {summary['fase1_general']['media_horas']} horas ({summary['fase1_general']['media_horas']*60:.1f} minutos)")
    print(f"Tiempo de espera antes de Fase 2: {summary['espera_fase2_general']['media_horas']} horas")
    print(f"Tiempo de ciclo total promedio: {summary['tiempo_ciclo_total_general']['media_horas']} horas")
    for fmt, data in summary["por_tipo_contenido"].items():
        print(f" - {fmt} (n={data['n']}): Fase 1 = {data['fase1_media_h']}h, Espera = {data['espera_media_h']}h, Total = {data['total_media_h']}h")

if __name__ == "__main__":
    analyze_baseline()
