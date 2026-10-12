-- Make batch positions unique within each brand, not globally.
DROP INDEX IF EXISTS idx_ideas_generation_batch_position;

CREATE UNIQUE INDEX idx_ideas_generation_batch_position
    ON ideas_generadas (brand_id, generation_batch_id, generation_index)
    WHERE generation_batch_id IS NOT NULL;
