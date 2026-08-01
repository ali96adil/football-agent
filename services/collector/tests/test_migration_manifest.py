from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault("APP_DB_NAME", "football_intelligence")
os.environ.setdefault("APP_DB_USER", "football_app")
os.environ.setdefault("APP_DB_PASSWORD", "test")
os.environ.setdefault("MIGRATIONS_ROOT", str(ROOT))
sys.path.insert(0, str(ROOT / "services/collector"))

from scripts import migrate  # noqa: E402


class MigrationManifestTests(unittest.TestCase):
    def test_relative_environment_root_is_independent_of_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"MIGRATIONS_ROOT": "../.."}, clear=False):
                previous = Path.cwd()
                try:
                    os.chdir(directory)
                    self.assertEqual(migrate.discover_root(), ROOT)
                finally:
                    os.chdir(previous)

    def test_repository_relative_environment_root_uses_stable_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"MIGRATIONS_ROOT": "."}, clear=False):
                previous = Path.cwd()
                try:
                    os.chdir(directory)
                    self.assertEqual(migrate.discover_root(), ROOT)
                finally:
                    os.chdir(previous)

    def test_default_root_is_independent_of_cwd(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("MIGRATIONS_ROOT", None)
                previous = Path.cwd()
                try:
                    os.chdir(directory)
                    self.assertEqual(migrate.discover_root(), ROOT)
                finally:
                    os.chdir(previous)

    def test_invalid_root_reports_required_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(
                RuntimeError, "database/migrations and services/collector"
            ):
                migrate.discover_root(directory)

    def test_manifest_has_unique_versions_and_real_files(self):
        versions = [version for version, _ in migrate.MIGRATIONS]
        self.assertEqual(len(versions), len(set(versions)))
        for _, path in migrate.MIGRATIONS:
            self.assertTrue(path.is_file(), path)
            self.assertEqual(len(migrate.checksum(path)), 64)

    def test_only_known_legacy_files_have_transaction_control(self):
        for version, path in migrate.MIGRATIONS:
            normalized = migrate.normalize_sql(version, path.read_text())
            self.assertFalse(
                any(migrate.TRANSACTION_CONTROL.fullmatch(line) for line in normalized.splitlines())
            )

    def test_new_transaction_control_is_rejected(self):
        with self.assertRaises(RuntimeError):
            migrate.normalize_sql("009_new", "BEGIN;\nSELECT 1;\nCOMMIT;\n")

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

    def test_worker_operations_migration_has_heartbeat_and_scheduler_state(self):
        content = (ROOT / "database/migrations/009_add_worker_operations.sql").read_text()
        self.assertIn("core.worker_heartbeats", content)
        self.assertIn("next_sync_at", content)
        self.assertIn("current_job_id UUID REFERENCES core.jobs", content)

    def test_auth_migration_has_sessions_rbac_and_audit(self):
        content = (ROOT / "database/migrations/010_add_auth_rbac.sql").read_text()
        for required in ("core.users", "core.user_sessions", "core.login_attempts", "core.audit_log"):
            self.assertIn(required, content)
        self.assertIn("admin", content)
        self.assertIn("operator", content)
        self.assertIn("viewer", content)

    def test_operations_migration_records_results_and_settings(self):
        content = (ROOT / "database/migrations/011_add_product_operations.sql").read_text()
        self.assertIn("result JSONB", content)
        self.assertIn("requested_by", content)
        self.assertIn("core.system_settings", content)
