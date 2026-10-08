-- Brand knowledge, provenance and channel ownership.

CREATE TABLE IF NOT EXISTS brand_sources (
    id BIGSERIAL PRIMARY KEY,
    organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
    brand_id BIGINT REFERENCES brands(id) ON DELETE CASCADE,
    scope VARCHAR(16) NOT NULL CHECK (scope IN ('global', 'organization', 'brand')),
    source_type VARCHAR(48) NOT NULL,
    title VARCHAR(320) NOT NULL DEFAULT '',
    url TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    content_hash VARCHAR(128),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    fetched_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((scope = 'global' AND organization_id IS NULL AND brand_id IS NULL)
        OR (scope = 'organization' AND organization_id IS NOT NULL AND brand_id IS NULL)
        OR (scope = 'brand' AND brand_id IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS brand_documents (
    id BIGSERIAL PRIMARY KEY,
    source_id BIGINT REFERENCES brand_sources(id) ON DELETE SET NULL,
    organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
    brand_id BIGINT REFERENCES brands(id) ON DELETE CASCADE,
    scope VARCHAR(16) NOT NULL CHECK (scope IN ('global', 'organization', 'brand')),
    title VARCHAR(320) NOT NULL,
    mime_type VARCHAR(128) NOT NULL DEFAULT 'text/plain',
    content TEXT NOT NULL,
    content_hash VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ready',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((scope = 'global' AND organization_id IS NULL AND brand_id IS NULL)
        OR (scope = 'organization' AND organization_id IS NOT NULL AND brand_id IS NULL)
        OR (scope = 'brand' AND brand_id IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS brand_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL REFERENCES brand_documents(id) ON DELETE CASCADE,
    organization_id BIGINT REFERENCES organizations(id) ON DELETE CASCADE,
    brand_id BIGINT REFERENCES brands(id) ON DELETE CASCADE,
    scope VARCHAR(16) NOT NULL CHECK (scope IN ('global', 'organization', 'brand')),
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (document_id, chunk_index)
);

CREATE TABLE IF NOT EXISTS brand_evidence (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT REFERENCES brands(id) ON DELETE CASCADE,
    source_id BIGINT REFERENCES brand_sources(id) ON DELETE SET NULL,
    document_id BIGINT REFERENCES brand_documents(id) ON DELETE SET NULL,
    chunk_id BIGINT REFERENCES brand_chunks(id) ON DELETE SET NULL,
    claim TEXT NOT NULL,
    evidence_text TEXT NOT NULL,
    confidence NUMERIC(5,4),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS brand_channels (
    id BIGSERIAL PRIMARY KEY,
    brand_id BIGINT NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    provider VARCHAR(64) NOT NULL,
    external_id VARCHAR(320) NOT NULL,
    display_name VARCHAR(320) NOT NULL DEFAULT '',
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    credential_reference TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provider, external_id)
);

CREATE INDEX IF NOT EXISTS idx_brand_sources_scope ON brand_sources(scope, organization_id, brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_documents_scope ON brand_documents(scope, organization_id, brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_chunks_scope ON brand_chunks(scope, organization_id, brand_id);
CREATE INDEX IF NOT EXISTS idx_brand_chunks_embedding ON brand_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_brand_evidence_brand ON brand_evidence(brand_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_brand_channels_brand ON brand_channels(brand_id, status);
