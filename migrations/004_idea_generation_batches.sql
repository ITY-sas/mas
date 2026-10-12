-- Track generated ideas by batch and position; legacy ideas remain unbatched.
ALTER TABLE ideas_generadas
    ADD COLUMN IF NOT EXISTS generation_batch_id UUID;

ALTER TABLE ideas_generadas
    ADD COLUMN IF NOT EXISTS generation_index SMALLINT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_ideas_generation_batch_position
    ON ideas_generadas (brand_id, generation_batch_id, generation_index)
    WHERE generation_batch_id IS NOT NULL;