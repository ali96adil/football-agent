#!/usr/bin/env python3
"""Check required Compose dotenv names without evaluating or printing values."""
from __future__ import annotations

from pathlib import Path
import re
import sys


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: check_env_names.py ENV_FILE NAME [NAME ...]")
    path = Path(sys.argv[1])
    assignment = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=")
    names: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = assignment.match(line)
        if match:
            names.add(match.group(1))
    missing = sorted(set(sys.argv[2:]) - names)
    if missing:
        raise SystemExit("Missing required .env variable names: " + ", ".join(missing))
    print("Required .env variable names are present (values were not printed).")


if __name__ == "__main__":
    main()
