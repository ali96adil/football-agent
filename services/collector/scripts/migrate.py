"""Checksum-protected migrations for football_intelligence only."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import psycopg

from app.config import build_database_url

# /app in the production image; CI supplies the repository root explicitly.
ROOT = Path(os.getenv("MIGRATIONS_ROOT", "/app"))
MIGRATIONS = (
    ("001_core_schema", ROOT / "database/001_core_schema.sql"),
    ("002_seed_sources", ROOT / "database/002_seed_sources.sql"),
    ("005_add_standings", ROOT / "database/migrations/005_add_standings.sql"),
    ("006_add_team_snapshots", ROOT / "database/migrations/006_add_team_snapshots.sql"),
    ("007_add_match_predictions", ROOT / "database/migrations/007_add_match_predictions.sql"),
    ("007_add_overall_rating", ROOT / "database/migrations/007_add_overall_rating.sql"),
    ("008_add_job_queue", ROOT / "database/migrations/008_add_job_queue.sql"),
)


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_target() -> None:
    if os.getenv("APP_DB_NAME") != "football_intelligence":
        raise RuntimeError("Refusing migration: APP_DB_NAME must be exactly football_intelligence")


def run() -> None:
    validate_target()
    with psycopg.connect(build_database_url(), autocommit=False) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE SCHEMA IF NOT EXISTS core")
            cursor.execute("""CREATE TABLE IF NOT EXISTS core.schema_migrations (
                version TEXT PRIMARY KEY, checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
            for version, path in MIGRATIONS:
                digest = checksum(path)
                cursor.execute("SELECT checksum FROM core.schema_migrations WHERE version = %s", (version,))
                existing = cursor.fetchone()
                if existing:
                    if existing[0] != digest:
                        raise RuntimeError(f"Checksum mismatch for applied migration {version}")
                    continue
                cursor.execute(path.read_text(encoding="utf-8"))
                cursor.execute(
                    "INSERT INTO core.schema_migrations (version, checksum) VALUES (%s, %s)",
                    (version, digest),
                )
        connection.commit()


if __name__ == "__main__":
    run()
