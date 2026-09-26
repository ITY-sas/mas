"""
Genera embeddings para registros existentes que no los tienen.
Uso: python backfill_embeddings.py
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from shared_tools import execute_db, generate_embedding, embedding_to_vector, query_db


def backfill_table(table: str, content_col: str = "content"):
    """Genera embeddings para registros de una tabla que no lo tienen."""
    allowed = {"tendencias", "referencias_competencia", "ideas_generadas", "publicaciones_generadas", "clientes"}
    if table not in allowed:
        print(f"  Tabla no permitida: {table}")
        return 0

    # La tabla clientes usa perfil_marca como contenido principal
    if table == "clientes":
        content_col = "perfil_marca"

    rows = query_db(f"SELECT id, {content_col} FROM {table} WHERE embedding IS NULL")
    if not rows:
        print(f"  ✓ {table}: todos los registros ya tienen embedding")
        return 0

    count = 0
    for row in rows:
        content = row[content_col]
        if not content:
            continue
        emb = generate_embedding(content)
        if emb:
            vec = embedding_to_vector(emb)
            execute_db(
                f"UPDATE {table} SET embedding = %s::vector WHERE id = %s",
                (vec, row["id"]),
            )
            count += 1
    print(f"  ✓ {table}: {count} embeddings generados (de {len(rows)} pendientes)")
    return count


if __name__ == "__main__":
    print("═══ Backfill de embeddings ═══\n")
    total = 0
    for tbl in ["tendencias", "referencias_competencia", "ideas_generadas", "publicaciones_generadas", "clientes"]:
        total += backfill_table(tbl)
    print(f"\n✅ Total: {total} embeddings generados")
