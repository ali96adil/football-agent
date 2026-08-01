ALTER TABLE core.data_sources
    ADD COLUMN IF NOT EXISTS provider TEXT,
    ADD COLUMN IF NOT EXISTS base_url TEXT,
    ADD COLUMN IF NOT EXISTS capabilities TEXT[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS secret_ciphertext BYTEA;

UPDATE core.data_sources SET
    provider = 'football_data',
    base_url = COALESCE(base_url, 'https://api.football-data.org/v4'),
    capabilities = ARRAY['competitions','fixtures','teams','standings']
WHERE code = 'football_data' AND provider IS NULL;

UPDATE core.data_sources SET
    provider = 'api_football',
    base_url = COALESCE(base_url, 'https://v3.football.api-sports.io'),
    capabilities = ARRAY['competitions','fixtures','teams','standings']
WHERE code = 'api_football' AND provider IS NULL;
