from __future__ import annotations

import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import check_env_names, ci_assert_compose


ROOT = Path(__file__).resolve().parents[2]


class TtyInput(io.StringIO):
    def isatty(self) -> bool:
        return True

    def read(self, *args, **kwargs):
        raise AssertionError("TTY input must not be read")


class ComposeVariableTests(unittest.TestCase):
    @staticmethod
    def compose_with_environment(entries: str) -> str:
        indented = "\n".join(f"      {line}" for line in entries.splitlines())
        return f"services:\n  app:\n    image: alpine\n    environment:\n{indented}\n"

    def test_extracts_supported_compose_expressions(self) -> None:
        contents = self.compose_with_environment(
            "PLAIN: ${PLAIN}\nDEFAULT: ${WITH_DEFAULT:-default}\nREQUIRED: ${REQUIRED_VAR:?error}"
        )
        self.assertEqual(
            check_env_names.compose_variable_names(contents),
            {"PLAIN", "WITH_DEFAULT", "REQUIRED_VAR"},
        )

    def test_ignores_container_time_expression(self) -> None:
        contents = self.compose_with_environment(
            "RUNTIME_A: $$RUNTIME_ONLY\nRUNTIME_B: $${RUNTIME_ONLY}"
        )
        self.assertEqual(check_env_names.compose_variable_names(contents), set())

    def test_extracts_unbraced_compose_expressions(self) -> None:
        contents = self.compose_with_environment(
            "UNBRACED: $UNBRACED\nEMBEDDED: value-$UNBRACED"
        )
        self.assertEqual(check_env_names.compose_variable_names(contents), {"UNBRACED"})

    def test_ignores_github_actions_expression(self) -> None:
        contents = self.compose_with_environment("GITHUB: $${{ github.ref }}")
        self.assertEqual(check_env_names.compose_variable_names(contents), set())

    def test_ignores_yaml_comments_and_single_quoted_scalars(self) -> None:
        contents = """
# $COMMENT_ONLY
services:
  app:
    image: alpine # ${END_COMMENT}
    environment:
      SINGLE: '$SINGLE_QUOTED'
      SINGLE_BRACED: '${SINGLE_BRACED}'
      DOUBLE: "$DOUBLE_QUOTED"
      PLAIN: $PLAIN
"""
        self.assertEqual(
            check_env_names.compose_variable_names(contents),
            {"DOUBLE_QUOTED", "PLAIN"},
        )

    def test_hash_without_yaml_comment_separation_remains_scalar_text(self) -> None:
        contents = self.compose_with_environment("HASH: prefix#$ACTIVE")
        self.assertEqual(check_env_names.compose_variable_names(contents), {"ACTIVE"})

    def test_missing_unbraced_variable_fails_env_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_file = root / ".env"
            compose_file = root / "compose.yaml"
            env_file.write_text("PRESENT=value\n", encoding="utf-8")
            compose_file.write_text(
                self.compose_with_environment("VALUE: $UNBRACED"), encoding="utf-8"
            )

            with patch.object(
                sys,
                "argv",
                ["check_env_names.py", str(env_file), str(compose_file)],
            ), self.assertRaisesRegex(SystemExit, "UNBRACED"):
                check_env_names.main()

    def test_inactive_variables_do_not_fail_env_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env_file = root / ".env"
            compose_file = root / "compose.yaml"
            env_file.write_text("PRESENT=value\n", encoding="utf-8")
            compose_file.write_text(
                self.compose_with_environment(
                    "# $COMMENT_ONLY\nVALUE: '$SINGLE_ONLY' # $END_COMMENT"
                ),
                encoding="utf-8",
            )

            with patch.object(
                sys,
                "argv",
                ["check_env_names.py", str(env_file), str(compose_file)],
            ), patch("sys.stdout", new_callable=io.StringIO):
                check_env_names.main()


class ComposeModelInputTests(unittest.TestCase):
    @staticmethod
    def completed(returncode: int = 0, stdout: str = "{}", stderr: str = ""):
        return subprocess.CompletedProcess([], returncode, stdout, stderr)

    def test_direct_tty_invocation_uses_compose_without_reading(self) -> None:
        with patch.object(sys, "stdin", TtyInput()), patch.object(
            ci_assert_compose.subprocess, "run", return_value=self.completed()
        ) as run:
            self.assertEqual(ci_assert_compose.load_compose_model(), {})
        run.assert_called_once()

    def test_pipe_json_is_used_without_running_compose(self) -> None:
        with patch.object(sys, "stdin", io.StringIO('{"services": {}}')), patch.object(
            ci_assert_compose.subprocess, "run"
        ) as run:
            self.assertEqual(ci_assert_compose.load_compose_model(), {"services": {}})
        run.assert_not_called()

    def test_invalid_piped_json_is_not_replaced_by_fallback(self) -> None:
        with patch.object(sys, "stdin", io.StringIO("not-json")), patch.object(
            ci_assert_compose.subprocess, "run"
        ) as run, self.assertRaisesRegex(SystemExit, "invalid Compose JSON"):
            ci_assert_compose.load_compose_model()
        run.assert_not_called()

    def test_empty_noninteractive_input_uses_fallback(self) -> None:
        with patch.object(sys, "stdin", io.StringIO("")), patch.object(
            ci_assert_compose.subprocess, "run", return_value=self.completed()
        ) as run:
            self.assertEqual(ci_assert_compose.load_compose_model(), {})
        run.assert_called_once()

    def test_compose_failure_is_propagated(self) -> None:
        failure = self.completed(returncode=23, stdout="", stderr="compose failed")
        with patch.object(sys, "stdin", TtyInput()), patch.object(
            ci_assert_compose.subprocess, "run", return_value=failure
        ), patch("sys.stderr", new_callable=io.StringIO) as stderr, self.assertRaises(
            SystemExit
        ) as raised:
            ci_assert_compose.load_compose_model()
        self.assertEqual(raised.exception.code, 23)
        self.assertEqual(stderr.getvalue(), "compose failed\n")


class ComposeRuntimeTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                str(ROOT / ".env.ci"),
                "config",
                "--format",
                "json",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        cls.model = json.loads(result.stdout)

    def test_current_model_has_routable_proxy_and_importable_worker(self) -> None:
        ci_assert_compose.assert_compose_model(copy.deepcopy(self.model))

    def test_internal_only_proxy_is_rejected(self) -> None:
        model = copy.deepcopy(self.model)
        ingress = next(name for name in model["networks"] if name.endswith("football_ingress"))
        model["services"]["proxy"]["networks"].pop(ingress)

        with self.assertRaisesRegex(SystemExit, "proxy must join football_ingress"):
            ci_assert_compose.assert_compose_model(model)

    def test_worker_script_path_invocation_is_rejected(self) -> None:
        model = copy.deepcopy(self.model)
        model["services"]["worker"]["command"] = ["python", "scripts/worker.py"]

        with self.assertRaisesRegex(SystemExit, "worker must run as a module"):
            ci_assert_compose.assert_compose_model(model)


if __name__ == "__main__":
    unittest.main()
