import psycopg2
import json
import csv
import os

def consolidate_60_cases():
    conn = psycopg2.connect("postgresql://postgres:password@127.0.0.1:5432/ideation_db")
    cur = conn.cursor()
    
    brand_map = {1: "EcoBrand", 2: "TechStart", 3: "FitLife"}
    consolidated_records = []
    
    for brand_id in [1, 2, 3]:
        # Query 20 ideas with their corresponding publications for this brand
        cur.execute("""
            SELECT 
                i.id as idea_id,
                p.id as pub_id,
                i.brand_id,
                i.content as idea_content,
                p.content as pub_content,
                p.platform,
                i.created_at as idea_time,
                p.created_at as pub_time
            FROM ideas_generadas i
            JOIN publicaciones_generadas p ON i.id = p.idea_id
            WHERE i.brand_id = %s
            ORDER BY i.id DESC
            LIMIT 20;
        """, (brand_id,))
        
        rows = cur.fetchall()
        print(f"Marca {brand_map[brand_id]} (ID {brand_id}): {len(rows)} pares idea-publicación recuperados.")
        
        for idx, r in enumerate(reversed(rows), 1):
            idea_id, pub_id, b_id, raw_idea, raw_pub, platform, idea_t, pub_t = r
            
            # Parse dossier
            try:
                dossier = json.loads(raw_idea)
                title = dossier.get("title", f"Idea {idea_id}")
                content_format = dossier.get("content_type") or ("reel" if "script" in dossier or "scenes" in dossier else "post")
            except Exception:
                title = raw_idea[:40]
                content_format = "post"
                
            record = {
                "case_index": len(consolidated_records) + 1,
                "case_id_brand": f"{brand_map[brand_id][:3].upper()}-{idx:02d}",
                "brand_id": b_id,
                "brand_name": brand_map[brand_id],
                "idea_id": idea_id,
                "publication_id": pub_id,
                "content_format": content_format,
                "title": title,
                "platform": platform,
                "idea_created_at": str(idea_t),
                "pub_created_at": str(pub_t),
                "copy_snippet": (raw_pub or "")[:120].replace("\n", " "),
                "status": "completed",
                "success": True
            }
            consolidated_records.append(record)
            
    conn.close()
    
    # Save JSON and CSV
    json_path = "docs/resultado_pruebas/dataset_60_casos_reales.json"
    csv_path = "docs/resultado_pruebas/dataset_60_casos_reales.csv"
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(consolidated_records, f, indent=2, ensure_ascii=False)
        
    keys = list(consolidated_records[0].keys())
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(consolidated_records)
        
    print(f"\nConsolidación terminada: Total {len(consolidated_records)} registros exportados.")
    print(f"Archivos guardados en {json_path} y {csv_path}")

if __name__ == "__main__":
    consolidate_60_cases()
