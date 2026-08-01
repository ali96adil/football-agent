from __future__ import annotations

import argparse
import getpass
import re

import psycopg

from app.config import build_database_url
from app.security import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactively create the first Football Agent admin")
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args()
    username = args.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,63}", username):
        raise SystemExit("invalid username format")
    password = getpass.getpass("Admin password: ")
    confirmation = getpass.getpass("Confirm admin password: ")
    if password != confirmation:
        raise SystemExit("passwords do not match")
    encoded = hash_password(password)
    with psycopg.connect(build_database_url()) as connection:
        existing = connection.execute("SELECT COUNT(*) FROM core.users WHERE role='admin'").fetchone()[0]
        if existing:
            raise SystemExit("an admin already exists; use the authenticated user-management API")
        connection.execute(
            "INSERT INTO core.users (username, display_name, password_hash, role) VALUES (%s, %s, %s, 'admin')",
            (username, args.display_name.strip(), encoded),
        )
    print(f"Admin {username} created.")


if __name__ == "__main__":
    main()
