"""Atomic, checksum-protected migrations for football_intelligence only."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
from typing import Callable

import psycopg

# Make ``app`` importable both from a repository checkout and from /app in the
# collector image. This depends on this file's location, never the caller's cwd.
COLLECTOR_ROOT = Path(__file__).resolve().parent.parent
if str(COLLECTOR_ROOT) not in sys.path:
    sys.path.insert(0, str(COLLECTOR_ROOT))

from app.config import build_database_url  # noqa: E402


MIGRATION_PATHS = (
    ("001_core_schema", "database/001_core_schema.sql"),
    ("002_seed_sources", "database/002_seed_sources.sql"),
    ("005_add_standings", "database/migrations/005_add_standings.sql"),
    ("006_add_team_snapshots", "database/migrations/006_add_team_snapshots.sql"),
    ("007_add_match_predictions", "database/migrations/007_add_match_predictions.sql"),
    ("007_add_overall_rating", "database/migrations/007_add_overall_rating.sql"),
    ("008_add_job_queue", "database/migrations/008_add_job_queue.sql"),
)

# These files predate the atomic runner and may already be recorded by checksum
# on existing databases. Keep their bytes unchanged; strip only their known,
# standalone transaction-control lines at execution time. New migrations with
# BEGIN/COMMIT/ROLLBACK are rejected.
LEGACY_TRANSACTION_CONTROL = {
    "001_core_schema": ("BEGIN", "COMMIT"),
    "006_add_team_snapshots": ("COMMIT",),
    "007_add_overall_rating": ("BEGIN", "COMMIT"),
    "008_add_job_queue": ("BEGIN", "COMMIT"),
}
TRANSACTION_CONTROL = re.compile(
    r"^\s*(BEGIN|COMMIT|ROLLBACK)(?:\s+TRANSACTION)?\s*;?\s*(?:--.*)?$", re.IGNORECASE
)


def _root_layout(root: Path) -> str | None:
    """Return the supported layout at *root*, if any.

    Repository checkouts must contain both ``database/migrations`` and
    ``services/collector``. The collector image intentionally flattens the
    latter into ``/app``; that layout is accepted only at this script's own
    collector root and must still contain ``database/migrations``.
    """
    if (root / "database/migrations").is_dir() and (root / "services/collector").is_dir():
        return "repository"
    if (
        root == COLLECTOR_ROOT
        and (root / "database/migrations").is_dir()
        and (root / "app").is_dir()
        and (root / "scripts/migrate.py").is_file()
    ):
        return "image"
    return None


def _validate_root(root: Path) -> Path:
    resolved = root.expanduser().resolve()
    if _root_layout(resolved) is None:
        raise RuntimeError(
            f"Invalid migrations root: {resolved}; expected database/migrations "
            "and services/collector (or the collector image layout)"
        )
    return resolved


def _default_root() -> Path:
    workspace = os.getenv("GITHUB_WORKSPACE")
    if workspace:
        candidate = Path(workspace).expanduser().resolve()
        if _root_layout(candidate) is not None:
            return candidate

    for candidate in (COLLECTOR_ROOT, *COLLECTOR_ROOT.parents):
        if _root_layout(candidate) is not None:
            return candidate
    raise RuntimeError(
        "Cannot locate migrations root containing database/migrations and services/collector"
    )


def discover_root(explicit: str | None = None) -> Path:
    """Find the migrations root without consulting the caller's cwd.

    Relative ``--migrations-root`` and ``MIGRATIONS_ROOT`` values are resolved
    first from ``COLLECTOR_ROOT`` (matching the CI working-directory contract),
    then from the discovered repository/image root. A valid
    ``GITHUB_WORKSPACE`` is preferred during that discovery. The caller's cwd
    is never a candidate.
    """
    configured = explicit if explicit is not None else os.getenv("MIGRATIONS_ROOT")
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.is_absolute():
            return _validate_root(candidate)

        bases = (COLLECTOR_ROOT, _default_root())
        checked: list[Path] = []
        for base in bases:
            resolved = (base / candidate).resolve()
            if resolved in checked:
                continue
            checked.append(resolved)
            if _root_layout(resolved) is not None:
                return resolved
        raise RuntimeError(
            f"Invalid relative migrations root: {configured!r}; checked "
            f"{', '.join(map(str, checked))}; expected database/migrations "
            "and services/collector (or the collector image layout)"
        )
    return _default_root()


def build_manifest(root: Path) -> tuple[tuple[str, Path], ...]:
    return tuple((version, root / relative) for version, relative in MIGRATION_PATHS)


ROOT = discover_root()
MIGRATIONS = build_manifest(ROOT)


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_sql(version: str, sql: str) -> str:
    controls: list[str] = []
    kept_lines: list[str] = []
    for line in sql.splitlines(keepends=True):
        match = TRANSACTION_CONTROL.fullmatch(line.rstrip("\r\n"))
        if match:
            controls.append(match.group(1).upper())
        else:
            kept_lines.append(line)

    allowed = LEGACY_TRANSACTION_CONTROL.get(version, ())
    if tuple(controls) != allowed:
        raise RuntimeError(
            f"Unexpected transaction control in {version}: {tuple(controls)!r}; expected {allowed!r}"
        )
    return "".join(kept_lines)


def validate_target() -> None:
    if os.getenv("APP_DB_NAME") != "football_intelligence":
        raise RuntimeError("Refusing migration: APP_DB_NAME must be exactly football_intelligence")


def ensure_metadata(connection: psycopg.Connection) -> None:
    with connection.transaction():
        connection.execute("CREATE SCHEMA IF NOT EXISTS core")
        connection.execute(
            """CREATE TABLE IF NOT EXISTS core.schema_migrations (
                version TEXT PRIMARY KEY, checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW())"""
        )


def apply_migration(
    connection: psycopg.Connection,
    version: str,
    path: Path,
    *,
    after_execute: Callable[[str, psycopg.Connection], None] | None = None,
) -> bool:
    """Apply SQL and record its original-file checksum in one transaction."""
    digest = checksum(path)
    sql = normalize_sql(version, path.read_text(encoding="utf-8"))
    with connection.transaction():
        # Serialize concurrent migration runners and re-check after the lock.
        connection.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (version,))
        existing = connection.execute(
            "SELECT checksum FROM core.schema_migrations WHERE version = %s", (version,)
        ).fetchone()
        if existing:
            if existing[0] != digest:
                raise RuntimeError(f"Checksum mismatch for applied migration {version}")
            return False

        connection.execute(sql)
        if after_execute is not None:
            after_execute(version, connection)
        connection.execute(
            "INSERT INTO core.schema_migrations (version, checksum) VALUES (%s, %s)",
            (version, digest),
        )
    return True


def run(
    *,
    migrations_root: str | None = None,
    after_execute: Callable[[str, psycopg.Connection], None] | None = None,
) -> None:
    validate_target()
    root = discover_root(migrations_root) if migrations_root else ROOT
    with psycopg.connect(build_database_url(), autocommit=True) as connection:
        ensure_metadata(connection)
        for version, path in build_manifest(root):
            apply_migration(connection, version, path, after_execute=after_execute)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrations-root", help="repository or image root containing database/")
    args = parser.parse_args()
    run(migrations_root=args.migrations_root)


if __name__ == "__main__":
    main()
