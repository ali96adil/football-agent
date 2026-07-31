from pathlib import Path
import os
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("APP_DB_NAME", "football_intelligence")
os.environ.setdefault("APP_DB_USER", "football_app")
os.environ.setdefault("APP_DB_PASSWORD", "test")
os.environ.setdefault("MIGRATIONS_ROOT", str(ROOT))
sys.path.insert(0, str(ROOT / "services/collector"))

from scripts import migrate  # noqa: E402


class MigrationManifestTests(unittest.TestCase):
    def test_manifest_has_unique_versions_and_real_files(self):
        versions = [version for version, _ in migrate.MIGRATIONS]
        self.assertEqual(len(versions), len(set(versions)))
        for _, path in migrate.MIGRATIONS:
            self.assertTrue(path.is_file(), path)
            self.assertEqual(len(migrate.checksum(path)), 64)

    def test_project_database_is_a_hard_guard(self):
        previous = os.environ.get("APP_DB_NAME")
        os.environ["APP_DB_NAME"] = "n8n"
        with self.assertRaises(RuntimeError):
            migrate.validate_target()
        os.environ["APP_DB_NAME"] = previous or "football_intelligence"

    def test_queue_migration_documents_skip_locked_and_recovery(self):
        content = (ROOT / "database/migrations/008_add_job_queue.sql").read_text()
        self.assertIn("dead_letter", content)
        queue = (ROOT / "services/collector/app/jobs.py").read_text()
        self.assertIn("FOR UPDATE SKIP LOCKED", queue)
        self.assertIn("recover_expired", queue)
