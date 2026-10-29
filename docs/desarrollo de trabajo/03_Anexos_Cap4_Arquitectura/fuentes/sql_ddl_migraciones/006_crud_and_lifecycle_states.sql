-- 006_crud_and_lifecycle_states.sql
-- Estados de ciclo de vida e inmutabilidad para Ideas, Publicaciones y Marcas

-- 1. Ideas generadas: ciclo de vida y soft delete
ALTER TABLE ideas_generadas
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'approved' NOT NULL;

ALTER TABLE ideas_generadas
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE ideas_generadas
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_ideas_active_brand_status
    ON ideas_generadas (brand_id, status)
    WHERE status != 'archived';

-- 2. Publicaciones generadas: ciclo de vida, inmutabilidad y soft delete
ALTER TABLE publicaciones_generadas
    ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'draft' NOT NULL;

ALTER TABLE publicaciones_generadas
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE publicaciones_generadas
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP;

CREATE INDEX IF NOT EXISTS idx_publications_active_brand_status
    ON publicaciones_generadas (brand_id, status)
    WHERE status != 'archived';

-- 3. Marcas: configuración dinámica de RAG
ALTER TABLE brands
    ADD COLUMN IF NOT EXISTS rag_config JSONB DEFAULT '{}'::jsonb;
