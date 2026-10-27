import psycopg2
import json

def setup_channels():
    conn = psycopg2.connect("postgresql://postgres:password@127.0.0.1:5432/ideation_db")
    cur = conn.cursor()
    
    channels = [
        (2, "linkedin", "techstart_li_001", "TechStart LinkedIn Official", "active", json.dumps({"__type": "linkedin"})),
        (3, "instagram", "fitlife_ig_001", "FitLife Instagram Official", "active", json.dumps({"__type": "instagram"}))
    ]
    
    for brand_id, provider, external_id, display_name, status, settings in channels:
        cur.execute("""
            INSERT INTO brand_channels (brand_id, provider, external_id, display_name, status, settings)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (provider, external_id) DO UPDATE 
            SET display_name = EXCLUDED.display_name, status = EXCLUDED.status, settings = EXCLUDED.settings;
        """, (brand_id, provider, external_id, display_name, status, settings))
        
    conn.commit()
    print("Database channels updated successfully.")
    
    cur.execute("SELECT id, brand_id, provider, external_id, display_name, status FROM brand_channels ORDER BY brand_id;")
    rows = cur.fetchall()
    for r in rows:
        print(f"Brand {r[1]}: {r[2]} ({r[3]}) - {r[4]} [{r[5]}]")
        
    conn.close()

if __name__ == "__main__":
    setup_channels()
