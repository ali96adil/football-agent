#!/usr/bin/env python3
"""Check required Compose dotenv names without evaluating or printing values."""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys


def mask_single_quoted_scalars(contents: str) -> str:
    """Hide single-quoted scalar contents while preserving the YAML layout."""
    output: list[str] = []
    state = "plain"
    index = 0
    scalar_boundaries = " \t:-,[{"

    while index < len(contents):
        character = contents[index]

        if state == "single":
            if character == "'":
                if index + 1 < len(contents) and contents[index + 1] == "'":
                    output.extend((" ", " "))
                    index += 2
                    continue
                state = "plain"
            output.append("\n" if character == "\n" else " ")
            index += 1
            continue

        previous = contents[index - 1] if index else "\n"
        if character == "'" and (previous in scalar_boundaries or previous == "\n"):
            output.append(" ")
            state = "single"
        else:
            output.append(character)
        index += 1

    return "".join(output)


def compose_variable_names(contents: str, project_directory: Path | None = None) -> set[str]:
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--project-directory",
            str(project_directory or Path.cwd()),
            "--env-file",
            "/dev/null",
            "-f",
            "-",
            "config",
            "--variables",
        ],
        input=mask_single_quoted_scalars(contents),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit("Unable to inspect Compose variables: docker compose config failed")

    lines = result.stdout.splitlines()
    return {line.split()[0] for line in lines[1:] if line.split()}


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: check_env_names.py ENV_FILE NAME_OR_COMPOSE_FILE [NAME ...]")
    path = Path(sys.argv[1])
    assignment = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = assignment.match(line)
        if match:
            names.add(match.group(1))

    required: set[str] = set()
    for argument in sys.argv[2:]:
        candidate = Path(argument)
        if candidate.suffix in {".yaml", ".yml"} and candidate.is_file():
            required.update(
                compose_variable_names(
                    candidate.read_text(encoding="utf-8"),
                    project_directory=candidate.resolve().parent,
                )
            )
        else:
            required.add(argument)

    missing = sorted(required - names)
    if missing:
        raise SystemExit("Missing required .env variable names: " + ", ".join(missing))
    print("Required .env variable names are present (values were not printed).")


if __name__ == "__main__":
    main()
