import time
import json
import csv
import requests
import os
import sys

ORCHESTRATOR_URL = "http://localhost:8002"

TEST_CASES = [
    {
        "test_id": "TC-01",
        "brand_id": 1,
        "brand_name": "EcoBrand",
        "content_format": "reel",
        "content": "Lanzamiento de protector solar biodegradable para temporada de vacaciones en Colombia, destacando ingredientes naturales y empaque compostable.",
        "integration_ids": ["cmv4uxozp0001ki7uwup1pdxh"]
    },
    {
        "test_id": "TC-02",
        "brand_id": 1,
        "brand_name": "EcoBrand",
        "content_format": "post",
        "content": "5 hábitos diarios prácticos para reducir la huella de plástico en el hogar sin gastar de más.",
        "integration_ids": ["cmv4uxozp0001ki7uwup1pdxh"]
    },
    {
        "test_id": "TC-03",
        "brand_id": 2,
        "brand_name": "TechStart",
        "content_format": "reel",
        "content": "Cómo automatizar la facturación electrónica en menos de 2 minutos para una panadería o cafetería independiente.",
        "integration_ids": ["techstart_li_001"]
    },
    {
        "test_id": "TC-04",
        "brand_id": 2,
        "brand_name": "TechStart",
        "content_format": "post",
        "content": "Comparativa de costos ocultos: datáfonos y terminales POS tradicionales frente a la pasarela digital ágil de TechStart.",
        "integration_ids": ["techstart_li_001"]
    },
    {
        "test_id": "TC-05",
        "brand_id": 3,
        "brand_name": "FitLife",
        "content_format": "reel",
        "content": "Rutina de movilidad articular y estiramiento de 10 minutos para personas que trabajan sentadas todo el día frente al computador.",
        "integration_ids": ["fitlife_ig_001"]
    },
    {
        "test_id": "TC-06",
        "brand_id": 3,
        "brand_name": "FitLife",
        "content_format": "post",
        "content": "Guía de suplementación basada en evidencia: desmitificando el uso de proteína aislada y creatina monohidrato en personas no deportistas.",
        "integration_ids": ["fitlife_ig_001"]
    }
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
            print(f"      [wait_for_task] advertencia consultando tarea: {e}")
        time.sleep(3)
    return {"status": "timeout", "error": f"Timeout tras {timeout}s esperando task {task_id}"}

def run_simulation():
    print("=" * 80)
    print("INICIANDO SIMULACIÓN EMPÍRICA EN TIEMPO REAL - MULTI-AGENTE (OE4)")
    print(f"Stack endpoint: {ORCHESTRATOR_URL}")
    print(f"Casos de prueba a ejecutar: {len(TEST_CASES)} (3 Marcas x 2 Formatos)")
    print("=" * 80)
    
    # Check stack health
    try:
        h = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=5).json()
        print(f"Orquestador online: {h.get('status')} (agentes: {h.get('agents')})")
    except Exception as e:
        print(f"ERROR: No se pudo contactar al orquestador: {e}")
        sys.exit(1)
        
    results = []
    
    for tc in TEST_CASES:
        print(f"\n>>> Ejecutando {tc['test_id']}: Marca '{tc['brand_name']}' (ID {tc['brand_id']}) | Formato: {tc['content_format'].upper()}")
        print(f"    Brief: \"{tc['content'][:70]}...\"")
        
        test_record = {
            "test_id": tc["test_id"],
            "brand_id": tc["brand_id"],
            "brand_name": tc["brand_name"],
            "content_format": tc["content_format"],
            "brief": tc["content"],
            "t_ideacion_seg": 0.0,
            "t_publicacion_seg": 0.0,
            "t_ciclo_total_seg": 0.0,
            "status_ideacion": "pending",
            "status_publicacion": "pending",
            "exito_global": False,
            "idea_id": None,
            "publication_id": None,
            "error_msg": None,
            "dossier_title": None,
            "schema_repaired": False,
            "variants_count": 0
        }
        
        # 1. Ejecutar Ideación
        t0_ideacion = time.perf_counter()
        ideation_payload = {
            "client_id": tc["brand_id"],
            "brand_id": tc["brand_id"],
            "content": tc["content"],
            "content_format": tc["content_format"],
            "wait": True,
            "timeout": 300.0
        }
        
        try:
            resp_ideacion = requests.post(
                f"{ORCHESTRATOR_URL}/process",
                json=ideation_payload,
                timeout=310.0
            )
            t_ideacion = time.perf_counter() - t0_ideacion
            test_record["t_ideacion_seg"] = round(t_ideacion, 2)
            
            if resp_ideacion.status_code == 200:
                data_ideacion = resp_ideacion.json()
                test_record["status_ideacion"] = "completed"
                test_record["idea_id"] = data_ideacion.get("idea_id")
                dossier = data_ideacion.get("preproduction") or {}
                test_record["dossier_title"] = dossier.get("title", "Sin título")
                print(f"    [IDEACIÓN OK] ({t_ideacion:.2f}s) Idea ID: {test_record['idea_id']} | Título: '{test_record['dossier_title']}'")
            else:
                test_record["status_ideacion"] = "failed"
                test_record["error_msg"] = f"HTTP {resp_ideacion.status_code}: {resp_ideacion.text[:200]}"
                print(f"    [IDEACIÓN FALLÓ] ({t_ideacion:.2f}s) Error: {test_record['error_msg']}")
                results.append(test_record)
                continue
        except Exception as e:
            t_ideacion = time.perf_counter() - t0_ideacion
            test_record["t_ideacion_seg"] = round(t_ideacion, 2)
            test_record["status_ideacion"] = "exception"
            test_record["error_msg"] = str(e)
            print(f"    [IDEACIÓN EXCEPCIÓN] ({t_ideacion:.2f}s) Error: {e}")
            results.append(test_record)
            continue
            
        # 2. Ejecutar Publicación
        t0_pub = time.perf_counter()
        pub_payload = {
            "brand_id": tc["brand_id"],
            "publish_mode": "draft",
            "integration_ids": tc["integration_ids"],
            "settings": {}
        }
        
        try:
            resp_pub = requests.post(
                f"{ORCHESTRATOR_URL}/ideas/{test_record['idea_id']}/publish",
                json=pub_payload,
                timeout=30.0
            )
            if resp_pub.status_code == 200:
                pub_dispatch = resp_pub.json()
                pub_task_id = pub_dispatch.get("task_id")
                print(f"    [PUBLICACIÓN INICIADA] Task ID: {pub_task_id}. Esperando finalización...")
                
                # Wait for publication task
                pub_task_data = wait_for_task(pub_task_id, timeout=240.0)
                t_pub = time.perf_counter() - t0_pub
                test_record["t_publicacion_seg"] = round(t_pub, 2)
                
                if pub_task_data.get("status") == "completed":
                    test_record["status_publicacion"] = "completed"
                    pub_res = pub_task_data.get("result") or {}
                    test_record["publication_id"] = pub_res.get("publication_id")
                    variants = pub_res.get("publication_variants") or []
                    test_record["variants_count"] = len(variants)
                    test_record["exito_global"] = True
                    print(f"    [PUBLICACIÓN OK] ({t_pub:.2f}s) Pub ID: {test_record['publication_id']} | Variantes: {test_record['variants_count']}")
                else:
                    test_record["status_publicacion"] = pub_task_data.get("status")
                    test_record["error_msg"] = pub_task_data.get("error")
                    print(f"    [PUBLICACIÓN FALLÓ] ({t_pub:.2f}s) Error: {test_record['error_msg']}")
            else:
                t_pub = time.perf_counter() - t0_pub
                test_record["t_publicacion_seg"] = round(t_pub, 2)
                test_record["status_publicacion"] = "failed"
                test_record["error_msg"] = f"HTTP {resp_pub.status_code}: {resp_pub.text[:200]}"
                print(f"    [PUBLICACIÓN FALLÓ DISPATCH] ({t_pub:.2f}s) Error: {test_record['error_msg']}")
        except Exception as e:
            t_pub = time.perf_counter() - t0_pub
            test_record["t_publicacion_seg"] = round(t_pub, 2)
            test_record["status_publicacion"] = "exception"
            test_record["error_msg"] = str(e)
            print(f"    [PUBLICACIÓN EXCEPCIÓN] ({t_pub:.2f}s) Error: {e}")
            
        test_record["t_ciclo_total_seg"] = round(test_record["t_ideacion_seg"] + test_record["t_publicacion_seg"], 2)
        print(f"    --> CICLO TOTAL CASO {tc['test_id']}: {test_record['t_ciclo_total_seg']}s | Éxito: {test_record['exito_global']}")
        results.append(test_record)
        
    # Guardar resultados
    json_path = "docs/resultado_pruebas/resultados_simulacion_real.json"
    csv_path = "docs/resultado_pruebas/resultados_simulacion_real.csv"
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    keys = list(results[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
        
    print("\n" + "=" * 80)
    print("RESUMEN FINAL DE LA SIMULACIÓN EMPÍRICA:")
    total = len(results)
    exitos = sum(1 for r in results if r["exito_global"])
    tasa_exito = (exitos / total) * 100
    t_prom_ideacion = sum(r["t_ideacion_seg"] for r in results) / total
    t_prom_pub = sum(r["t_publicacion_seg"] for r in results) / total
    t_prom_total = sum(r["t_ciclo_total_seg"] for r in results) / total
    
    print(f"- Total Casos Ejecutados: {total}")
    print(f"- Casos Exitosos: {exitos}/{total} ({tasa_exito:.1f}%)")
    print(f"- Tiempo Promedio Ideación: {t_prom_ideacion:.2f} s ({t_prom_ideacion/60:.2f} min)")
    print(f"- Tiempo Promedio Publicación: {t_prom_pub:.2f} s ({t_prom_pub/60:.2f} min)")
    print(f"- Tiempo Promedio Ciclo PoC: {t_prom_total:.2f} s ({t_prom_total/60:.2f} min)")
    print(f"- Archivos guardados: {json_path} y {csv_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_simulation()
