-- Multi-tenant foundation. Idempotent migration for existing installations.

CREATE TABLE IF NOT EXISTS organizations (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    slug VARCHAR(160) NOT NULL UNIQUE,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    display_name VARCHAR(160) NOT NULL DEFAULT '',
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS organization_members (
    organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL DEFAULT 'member',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, user_id)
);

CREATE TABLE IF NOT EXISTS brands (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(160) NOT NULL,
    slug VARCHAR(160) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ready',
    profile_marca TEXT,
    restricciones_tono TEXT,
    historico TEXT,
    producto_servicio TEXT,
    audiencia_objetivo TEXT,
    objetivo_marketing TEXT,
    propuesta_valor TEXT,
    pilares_contenido TEXT,
    canales_objetivo TEXT,
    pais VARCHAR(80) DEFAULT 'Colombia',
    zona_horaria VARCHAR(80) DEFAULT 'America/Bogota',
    restricciones_legales TEXT,
    embedding VECTOR(768),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, slug)
);

CREATE TABLE IF NOT EXISTS brand_members (
    brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL DEFAULT 'editor',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (brand_id, user_id)
);

CREATE TABLE IF NOT EXISTS legacy_client_brand (
    client_id INTEGER PRIMARY KEY REFERENCES clientes(id) ON DELETE CASCADE,
    brand_id BIGINT NOT NULL UNIQUE REFERENCES brands(id) ON DELETE CASCADE
);

ALTER TABLE ideas_generadas ADD COLUMN IF NOT EXISTS brand_id BIGINT;
ALTER TABLE publicaciones_generadas ADD COLUMN IF NOT EXISTS brand_id BIGINT;

CREATE INDEX IF NOT EXISTS idx_ideas_brand_created
    ON ideas_generadas (brand_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_publicaciones_brand_created
    ON publicaciones_generadas (brand_id, created_at DESC);

INSERT INTO organizations (name, slug)
VALUES ('Demo Colombia', 'demo-colombia')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO brands (
    organization_id, name, slug, profile_marca, restricciones_tono, historico,
    producto_servicio, audiencia_objetivo, objetivo_marketing, propuesta_valor,
    pilares_contenido, canales_objetivo, pais, zona_horaria, restricciones_legales
)
SELECT
    o.id, c.nombre, lower(regexp_replace(c.nombre, '[^a-zA-Z0-9]+', '-', 'g')),
    c.perfil_marca, c.restricciones_tono, c.historico, c.producto_servicio,
    c.audiencia_objetivo, c.objetivo_marketing, c.propuesta_valor,
    c.pilares_contenido, c.canales_objetivo, c.pais, c.zona_horaria,
    c.restricciones_legales
FROM clientes c
CROSS JOIN organizations o
WHERE o.slug = 'demo-colombia'
ON CONFLICT (organization_id, slug) DO UPDATE SET
    profile_marca = EXCLUDED.profile_marca,
    restricciones_tono = EXCLUDED.restricciones_tono,
    historico = EXCLUDED.historico,
    producto_servicio = EXCLUDED.producto_servicio,
    audiencia_objetivo = EXCLUDED.audiencia_objetivo,
    objetivo_marketing = EXCLUDED.objetivo_marketing,
    propuesta_valor = EXCLUDED.propuesta_valor,
    pilares_contenido = EXCLUDED.pilares_contenido,
    canales_objetivo = EXCLUDED.canales_objetivo,
    pais = EXCLUDED.pais,
    zona_horaria = EXCLUDED.zona_horaria,
    restricciones_legales = EXCLUDED.restricciones_legales,
    updated_at = now();

INSERT INTO legacy_client_brand (client_id, brand_id)
SELECT c.id, b.id
FROM clientes c
JOIN organizations o ON o.slug = 'demo-colombia'
JOIN brands b ON b.organization_id = o.id AND b.name = c.nombre
ON CONFLICT (client_id) DO UPDATE SET brand_id = EXCLUDED.brand_id;

UPDATE ideas_generadas i
SET brand_id = m.brand_id
FROM legacy_client_brand m
WHERE i.client_id = m.client_id AND i.brand_id IS NULL;

UPDATE publicaciones_generadas p
SET brand_id = m.brand_id
FROM legacy_client_brand m
WHERE p.client_id = m.client_id AND p.brand_id IS NULL;

-- Preserve historical rows with unknown client_id in a quarantine scope instead
-- of assigning them to a real brand or deleting them.
INSERT INTO organizations (name, slug)
VALUES ('Legacy quarantine', 'legacy-quarantine')
ON CONFLICT (slug) DO NOTHING;

INSERT INTO brands (organization_id, name, slug, status, profile_marca)
SELECT id, 'Legacy unassigned', 'legacy-unassigned', 'quarantined',
       'Historical records without a resolvable client_id; never use as brand context.'
FROM organizations
WHERE slug = 'legacy-quarantine'
ON CONFLICT (organization_id, slug) DO NOTHING;

UPDATE ideas_generadas i
SET brand_id = b.id
FROM brands b
JOIN organizations o ON o.id = b.organization_id
WHERE o.slug = 'legacy-quarantine' AND i.brand_id IS NULL;

UPDATE publicaciones_generadas p
SET brand_id = b.id
FROM brands b
JOIN organizations o ON o.id = b.organization_id
WHERE o.slug = 'legacy-quarantine' AND p.brand_id IS NULL;

ALTER TABLE ideas_generadas
    DROP CONSTRAINT IF EXISTS ideas_generadas_brand_id_fkey;
ALTER TABLE ideas_generadas
    ADD CONSTRAINT ideas_generadas_brand_id_fkey
    FOREIGN KEY (brand_id) REFERENCES brands(id);

ALTER TABLE publicaciones_generadas
    DROP CONSTRAINT IF EXISTS publicaciones_generadas_brand_id_fkey;
ALTER TABLE publicaciones_generadas
    ADD CONSTRAINT publicaciones_generadas_brand_id_fkey
    FOREIGN KEY (brand_id) REFERENCES brands(id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM ideas_generadas WHERE brand_id IS NULL
    ) THEN
        ALTER TABLE ideas_generadas ALTER COLUMN brand_id SET NOT NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM publicaciones_generadas WHERE brand_id IS NULL
    ) THEN
        ALTER TABLE publicaciones_generadas ALTER COLUMN brand_id SET NOT NULL;
    END IF;
END $$;
