INSERT INTO core.data_sources (
    code,
    name,
    source_type,
    priority,
    reliability_score,
    daily_request_limit,
    reserved_requests,
    metadata
)
VALUES
    (
        'football_data',
        'football-data.org',
        'api',
        80,
        0.90,
        NULL,
        0,
        '{"role":"fixture_discovery_and_validation"}'
    ),
    (
        'api_football',
        'API-Football',
        'api',
        90,
        0.92,
        100,
        20,
        '{"role":"deep_match_analysis"}'
    ),
    (
        'thesportsdb',
        'TheSportsDB',
        'api',
        50,
        0.65,
        NULL,
        0,
        '{"role":"team_identity_and_media"}'
    ),
    (
        'sportmonks',
        'Sportmonks',
        'api',
        75,
        0.85,
        NULL,
        0,
        '{"role":"experimental_comparison","enabled_by_default":false}'
    ),
    (
        'open_meteo',
        'Open-Meteo',
        'weather',
        60,
        0.85,
        10000,
        0,
        '{"role":"fixture_weather"}'
    ),
    (
        'official_team_site',
        'Official Team Website',
        'official_site',
        100,
        0.97,
        NULL,
        0,
        '{"role":"official_news_and_team_updates"}'
    )
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    priority = EXCLUDED.priority,
    reliability_score = EXCLUDED.reliability_score,
    daily_request_limit = EXCLUDED.daily_request_limit,
    reserved_requests = EXCLUDED.reserved_requests,
    metadata = EXCLUDED.metadata,
    updated_at = NOW();
