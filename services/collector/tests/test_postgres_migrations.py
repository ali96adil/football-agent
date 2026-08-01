from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

import psycopg

from app.config import build_database_url
from scripts import migrate


@unittest.skipUnless(
    os.getenv("RUN_POSTGRES_INTEGRATION") == "1",
    "set RUN_POSTGRES_INTEGRATION=1 against an ephemeral PostgreSQL database",
)
class PostgreSQLMigrationAtomicityTests(unittest.TestCase):
    def test_failure_between_sql_and_checksum_rolls_back_schema(self) -> None:
        version = "test_failure_atomicity"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "atomicity.sql"
            path.write_text("CREATE TABLE core.atomicity_probe (id integer PRIMARY KEY);\n")
            with psycopg.connect(build_database_url(), autocommit=True) as connection:
                migrate.ensure_metadata(connection)
                connection.execute("DROP TABLE IF EXISTS core.atomicity_probe")
                connection.execute(
                    "DELETE FROM core.schema_migrations WHERE version = %s", (version,)
                )

                def fail_after_sql(_version: str, _connection: psycopg.Connection) -> None:
                    raise RuntimeError("injected checksum-record failure")

                with self.assertRaisesRegex(RuntimeError, "injected"):
                    migrate.apply_migration(
                        connection,
                        version,
                        path,
                        after_execute=fail_after_sql,
                    )

                table = connection.execute(
                    "SELECT to_regclass('core.atomicity_probe')"
                ).fetchone()[0]
                recorded = connection.execute(
                    "SELECT 1 FROM core.schema_migrations WHERE version = %s", (version,)
                ).fetchone()
                self.assertIsNone(table)
                self.assertIsNone(recorded)
