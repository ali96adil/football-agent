BEGIN;
ALTER TABLE core.data_sources
    DROP COLUMN IF EXISTS secret_ciphertext,
    DROP COLUMN IF EXISTS capabilities,
    DROP COLUMN IF EXISTS base_url,
    DROP COLUMN IF EXISTS provider;
COMMIT;
