import time
import json
import csv
import requests
import os
import sys

ORCHESTRATOR_URL = "http://localhost:8002"

BRIEFS_TECHSTART = [
    {"format": "reel", "brief": "Cómo conciliar pagos de múltiples plataformas en un solo panel contable para restaurantes y cafeterías."},
    {"format": "post", "brief": "3 razones por las que un pequeño negocio pierde clientes al no aceptar transferencias inmediatas."},
    {"format": "reel", "brief": "Evita sanciones de la DIAN: Facturación electrónica automática en menos de 2 minutos con TechStart."},
    {"format": "post", "brief": "Guía rápida de seguridad financiera: qué es el cifrado de pagos punto a punto en comercios locales."},
    {"format": "reel", "brief": "De la libreta tradicional de cobros al link digital seguro en panaderías de barrio."},
    {"format": "post", "brief": "Infografía comparativa de comisiones por transacción entre banca tradicional y pasarelas ágiles."},
    {"format": "reel", "brief": "Cobros sin contacto con tecnología NFC desde el celular sin necesidad de comprar datáfono físico."},
    {"format": "post", "brief": "5 métricas de flujo de caja que todo dueño de cafetería o comercio debe revisar cada semana."},
    {"format": "reel", "brief": "Caso real: Cómo un comercio local aumentó sus ventas un 40% aceptando pagos con código QR interoperable."},
    {"format": "post", "brief": "Checklist de 4 pasos para formalizar los cobros digitales de una microempresa en Colombia."},
    {"format": "reel", "brief": "Alertas antifraude y detección de transacciones sospechosas en tiempo real para negocios."},
    {"format": "post", "brief": "Desmitificando el costo de la facturación electrónica para pequeños comerciantes y ferreterías."},
    {"format": "reel", "brief": "Cómo integrar cobros directos por WhatsApp en 3 pasos con botones de pago seguros."},
    {"format": "post", "brief": "Gestión de devoluciones y cancelaciones de compras sin alterar el inventario ni la contabilidad."},
    {"format": "reel", "brief": "Acceso a microcréditos para capital de trabajo basados en el volumen real de ventas digitales."},
    {"format": "post", "brief": "Reporte financiero semanal automatizado con gráficos de ventas enviado directamente a tu teléfono."}
]

BRIEFS_FITLIFE = [
    {"format": "reel", "brief": "3 errores comunes al consumir creatina monohidrato que disminuyen su efectividad y absorción."},
    {"format": "post", "brief": "Timing de nutrientes y proteína: evidencia científica sobre la supuesta ventana anabólica."},
    {"format": "reel", "brief": "Cómo preparar un batido de recuperación muscular equilibrado y saciante en menos de 2 minutos."},
    {"format": "post", "brief": "Comparativa nutricional: proteína aislada de suero de leche frente a proteína vegetal de arveja y arroz."},
    {"format": "reel", "brief": "Técnica de respiración diafragmática y activación del core para levantar peso sin dolor lumbar."},
    {"format": "post", "brief": "La relación directa entre las horas de sueño profundo y la tasa de síntesis proteica muscular."},
    {"format": "reel", "brief": "Opciones de snacks proteicos rápidos de menos de 150 calorías para evitar picos de glucosa en la oficina."},
    {"format": "post", "brief": "Desmitificando los quemadores de grasa comerciales: qué ingredientes tienen respaldo científico."},
    {"format": "reel", "brief": "Rutina de calentamiento dinámico de 5 minutos antes de entrenar hombro y pecho."},
    {"format": "post", "brief": "Importancia del balance de sodio, potasio y magnesio en sesiones de ejercicio de más de 60 minutos."},
    {"format": "reel", "brief": "Cómo leer la tabla nutricional de un suplemento y detectar azúcares añadidos bajo otros nombres."},
    {"format": "post", "brief": "Periodización del entrenamiento: por qué entrenar siempre al fallo muscular frena el progreso."}
]

def wait_for_task(task_id: str, timeout: float = 240.0) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            res = requests.get(f"{ORCHESTRATOR_URL}/tasks/{task_id}", timeout=10)
            if res.status_code == 200:
                data = res.json()
                status = data.get("status")
                if status in ("completed", "failed"):
                    return data
        except Exception as e:
            pass
        time.sleep(2)
    return {"status": "timeout", "error": f"Timeout tras {timeout}s"}

def run_campaign():
    print("=" * 80)
    print("EJECUTANDO CAMPAÑA DE GENERACIÓN Y PROGRAMACIÓN REAL (60 CASOS EN BASE DE DATOS)")
    print(f"Endpoint: {ORCHESTRATOR_URL}")
    print("=" * 80)
    
    # 1. Ejecutar para TechStart (Brand ID 2)
    print("\n>>> INICIANDO PROCESAMIENTO PARA MARCA 2: TECHSTART (16 nuevos briefs)...")
    for i, item in enumerate(BRIEFS_TECHSTART, 1):
        print(f"  [TechStart {i}/16] ({item['format'].upper()}) \"{item['brief'][:60]}...\"")
        t0 = time.perf_counter()
        
        # Ideación
        try:
            r = requests.post(f"{ORCHESTRATOR_URL}/process", json={
                "client_id": 2, "brand_id": 2, "content": item["brief"],
                "content_format": item["format"], "wait": True, "timeout": 300.0
            }, timeout=310.0)
            t_ide = time.perf_counter() - t0
            if r.status_code == 200:
                idea_data = r.json()
                idea_id = idea_data.get("idea_id")
                print(f"    -> Ideación OK (ID {idea_id}, {t_ide:.1f}s)")
                
                # Publicación
                t0_pub = time.perf_counter()
                r_pub = requests.post(f"{ORCHESTRATOR_URL}/ideas/{idea_id}/publish", json={
                    "brand_id": 2, "publish_mode": "draft",
                    "integration_ids": ["techstart_li_001"], "settings": {}
                }, timeout=30.0)
                if r_pub.status_code == 200:
                    pub_task_id = r_pub.json().get("task_id")
                    pub_res = wait_for_task(pub_task_id, timeout=240.0)
                    t_pub = time.perf_counter() - t0_pub
                    if pub_res.get("status") == "completed":
                        res_data = pub_res.get("result") or {}
                        pub_id = res_data.get("publication_id")
                        print(f"    -> Publicación OK (ID {pub_id}, {t_pub:.1f}s) Total: {t_ide+t_pub:.1f}s")
                    else:
                        print(f"    -> Publicación Falló: {pub_res.get('error')}")
                else:
                    print(f"    -> Publicación Error HTTP: {r_pub.status_code}")
            else:
                print(f"    -> Ideación Error HTTP: {r.status_code}")
        except Exception as e:
            print(f"    -> Excepción: {e}")
            
    # 2. Ejecutar para FitLife (Brand ID 3)
    print("\n>>> INICIANDO PROCESAMIENTO PARA MARCA 3: FITLIFE (12 nuevos briefs)...")
    for i, item in enumerate(BRIEFS_FITLIFE, 1):
        print(f"  [FitLife {i}/12] ({item['format'].upper()}) \"{item['brief'][:60]}...\"")
        t0 = time.perf_counter()
        
        # Ideación
        try:
            r = requests.post(f"{ORCHESTRATOR_URL}/process", json={
                "client_id": 3, "brand_id": 3, "content": item["brief"],
                "content_format": item["format"], "wait": True, "timeout": 300.0
            }, timeout=310.0)
            t_ide = time.perf_counter() - t0
            if r.status_code == 200:
                idea_data = r.json()
                idea_id = idea_data.get("idea_id")
                print(f"    -> Ideación OK (ID {idea_id}, {t_ide:.1f}s)")
                
                # Publicación
                t0_pub = time.perf_counter()
                r_pub = requests.post(f"{ORCHESTRATOR_URL}/ideas/{idea_id}/publish", json={
                    "brand_id": 3, "publish_mode": "draft",
                    "integration_ids": ["fitlife_ig_001"], "settings": {}
                }, timeout=30.0)
                if r_pub.status_code == 200:
                    pub_task_id = r_pub.json().get("task_id")
                    pub_res = wait_for_task(pub_task_id, timeout=240.0)
                    t_pub = time.perf_counter() - t0_pub
                    if pub_res.get("status") == "completed":
                        res_data = pub_res.get("result") or {}
                        pub_id = res_data.get("publication_id")
                        print(f"    -> Publicación OK (ID {pub_id}, {t_pub:.1f}s) Total: {t_ide+t_pub:.1f}s")
                    else:
                        print(f"    -> Publicación Falló: {pub_res.get('error')}")
                else:
                    print(f"    -> Publicación Error HTTP: {r_pub.status_code}")
            else:
                print(f"    -> Ideación Error HTTP: {r.status_code}")
        except Exception as e:
            print(f"    -> Excepción: {e}")

    # 3. Publicar cualquier idea existente previa que no tuviera publicación asociada
    print("\n>>> VERIFICANDO IDEAS SIN PUBLICACIÓN EN BASE DE DATOS...")
    try:
        import psycopg2
        conn = psycopg2.connect("postgresql://postgres:password@127.0.0.1:5432/ideation_db")
        cur = conn.cursor()
        cur.execute("""
            SELECT i.id, i.brand_id 
            FROM ideas_generadas i
            LEFT JOIN publicaciones_generadas p ON i.id = p.idea_id
            WHERE p.id IS NULL AND i.brand_id IN (1, 2, 3)
            ORDER BY i.id;
        """)
        unpub = cur.fetchall()
        print(f"Se encontraron {len(unpub)} ideas pendientes de publicación asociada.")
        channel_map = {1: "cmv4uxozp0001ki7uwup1pdxh", 2: "techstart_li_001", 3: "fitlife_ig_001"}
        for idea_id, brand_id in unpub:
            ch = channel_map.get(brand_id)
            if ch:
                print(f"  Publicando idea pendiente ID {idea_id} (Marca {brand_id})...")
                r_pub = requests.post(f"{ORCHESTRATOR_URL}/ideas/{idea_id}/publish", json={
                    "brand_id": brand_id, "publish_mode": "draft",
                    "integration_ids": [ch], "settings": {}
                }, timeout=30.0)
                if r_pub.status_code == 200:
                    pub_task_id = r_pub.json().get("task_id")
                    wait_for_task(pub_task_id, timeout=120.0)
        conn.close()
    except Exception as e:
        print(f"Aviso en verificación de publicaciones pendientes: {e}")

    print("\n" + "=" * 80)
    print("CAMPAÑA COMPLETADA CON ÉXITO")
    print("=" * 80)

if __name__ == "__main__":
    run_campaign()
