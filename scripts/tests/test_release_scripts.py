import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class RollbackSafetyTests(unittest.TestCase):
    def test_rollback_release_tree_outlives_compose_bind_mounts(self) -> None:
        script = (ROOT / "scripts" / "rollback.sh").read_text(encoding="utf-8")

        self.assertIn('release_root="$root/.rollback-releases"', script)
        self.assertIn('release_dir="$release_root/$revision"', script)
        self.assertNotIn('release_dir="$(mktemp -d)"', script)

    def test_rollback_requires_multiple_stable_container_checks(self) -> None:
        script = (ROOT / "scripts" / "rollback.sh").read_text(encoding="utf-8")

        self.assertIn("local stable_checks=0", script)
        self.assertIn("stable_restart_signature", script)
        self.assertIn(".RestartCount", script)
        self.assertIn('[[ "$stable_checks" -ge 3 ]] && return 0', script)


if __name__ == "__main__":
    unittest.main()
