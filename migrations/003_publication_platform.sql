-- Store the target platform for each generated publication variant.
ALTER TABLE publicaciones_generadas
    ADD COLUMN IF NOT EXISTS platform VARCHAR(64);

CREATE INDEX IF NOT EXISTS idx_publicaciones_brand_platform_created
    ON publicaciones_generadas (brand_id, platform, created_at DESC);
