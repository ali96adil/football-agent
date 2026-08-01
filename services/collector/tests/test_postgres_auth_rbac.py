from __future__ import annotations

import os
import unittest

import httpx

from app.auth import CSRF_COOKIE, SESSION_COOKIE
from app.db.connection import close_connection_pool, open_connection_pool, pool
from app.main import app
from app.security import hash_password, hash_secret


@unittest.skipUnless(
    os.getenv("RUN_POSTGRES_INTEGRATION") == "1",
    "set RUN_POSTGRES_INTEGRATION=1 against an ephemeral migrated PostgreSQL database",
)
class PostgreSQLAuthRBACTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        await open_connection_pool()
        self.identities: dict[str, tuple[str, str]] = {}
        async with pool.connection() as connection:
            await connection.execute("DELETE FROM core.users WHERE username LIKE 'rbac_test_%'")
            for role in ("viewer", "operator", "admin"):
                result = await connection.execute(
                    """INSERT INTO core.users (username, display_name, password_hash, role)
                       VALUES (%s, %s, %s, %s) RETURNING id""",
                    (f"rbac_test_{role}", role, hash_password("integration password 123"), role),
                )
                user_id = (await result.fetchone())["id"]
                token, csrf = f"token-{role}", f"csrf-{role}"
                await connection.execute(
                    """INSERT INTO core.user_sessions
                       (user_id, token_hash, csrf_hash, expires_at)
                       VALUES (%s, %s, %s, NOW() + INTERVAL '1 hour')""",
                    (user_id, hash_secret(token), hash_secret(csrf)),
                )
                self.identities[role] = (token, csrf)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        async with pool.connection() as connection:
            await connection.execute("DELETE FROM core.users WHERE username LIKE 'rbac_test_%'")
        await close_connection_pool()

    def auth(self, role: str, *, csrf: bool = False) -> dict:
        token, csrf_token = self.identities[role]
        result = {"cookies": {SESSION_COOKIE: token, CSRF_COOKIE: csrf_token}}
        if csrf:
            result["headers"] = {"x-csrf-token": csrf_token}
        return result

    async def test_complete_role_and_csrf_matrix(self) -> None:
        self.assertEqual((await self.client.get("/api/v1/admin/users", **self.auth("viewer"))).status_code, 403)
        self.assertEqual((await self.client.get("/api/v1/admin/users", **self.auth("operator"))).status_code, 403)
        self.assertEqual((await self.client.get("/api/v1/admin/users", **self.auth("admin"))).status_code, 200)
        payload = {
            "username": "rbac_test_created", "display_name": "Created User",
            "password": "created password 123", "role": "viewer",
        }
        self.assertEqual((await self.client.post("/api/v1/admin/users", json=payload, **self.auth("viewer", csrf=True))).status_code, 403)
        self.assertEqual((await self.client.post("/api/v1/admin/users", json=payload, **self.auth("operator", csrf=True))).status_code, 403)
        self.assertEqual((await self.client.post("/api/v1/admin/users", json=payload, **self.auth("admin"))).status_code, 403)
        response = await self.client.post("/api/v1/admin/users", json=payload, **self.auth("admin", csrf=True))
        self.assertEqual(response.status_code, 201, response.text)


if __name__ == "__main__":
    unittest.main()
