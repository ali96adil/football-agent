from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, patch

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
            await connection.execute("DELETE FROM core.data_sources WHERE code='rbac_test_source'")
            await connection.execute("DELETE FROM core.jobs WHERE requested_by IN (SELECT id FROM core.users WHERE username LIKE 'rbac_test_%')")
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
        self.assertEqual((await self.client.get("/api/v1/admin/telegram/destinations", **self.auth("viewer"))).status_code, 403)
        self.assertEqual((await self.client.get("/api/v1/admin/telegram/destinations", **self.auth("operator"))).status_code, 403)
        self.assertEqual((await self.client.get("/api/v1/admin/telegram/destinations", **self.auth("admin"))).status_code, 200)
        payload = {
            "username": "rbac_test_created", "display_name": "Created User",
            "password": "created password 123", "role": "viewer",
        }
        self.assertEqual((await self.client.post("/api/v1/admin/users", json=payload, **self.auth("viewer", csrf=True))).status_code, 403)
        self.assertEqual((await self.client.post("/api/v1/admin/users", json=payload, **self.auth("operator", csrf=True))).status_code, 403)
        self.assertEqual((await self.client.post("/api/v1/admin/users", json=payload, **self.auth("admin"))).status_code, 403)
        response = await self.client.post("/api/v1/admin/users", json=payload, **self.auth("admin", csrf=True))
        self.assertEqual(response.status_code, 201, response.text)

        action_payload = {"limit": 5, "window_size": 3, "fixture_days": 2}
        viewer_action = await self.client.post("/api/v1/operations/actions/evaluation", json=action_payload, **self.auth("viewer", csrf=True))
        self.assertEqual(viewer_action.status_code, 403)
        operator_action = await self.client.post("/api/v1/operations/actions/evaluation", json=action_payload, **self.auth("operator", csrf=True))
        self.assertEqual(operator_action.status_code, 202, operator_action.text)
        self.assertEqual(operator_action.json()["job_type"], "evaluate_predictions")
        await self.assert_source_management_is_admin_only_and_redacts_secret()

    async def assert_source_management_is_admin_only_and_redacts_secret(self) -> None:
        payload = {
            "code":"rbac_test_source","name":"RBAC source","source_type":"api",
            "provider":"football_data","base_url":"https://example.com/api",
            "priority":40,"capabilities":["fixtures"],"enabled":True,
            "secret":"integration-secret-value",
        }
        viewer = await self.client.post("/api/v1/operations/sources", json=payload, **self.auth("viewer", csrf=True))
        self.assertEqual(viewer.status_code, 403)
        operator = await self.client.post("/api/v1/operations/sources", json=payload, **self.auth("operator", csrf=True))
        self.assertEqual(operator.status_code, 403)
        with patch.dict(os.environ,{"SOURCE_SECRET_ENCRYPTION_KEY":"integration-only-encryption-key-123456789"}):
            created = await self.client.post("/api/v1/operations/sources", json=payload, **self.auth("admin", csrf=True))
        self.assertEqual(created.status_code, 201, created.text)
        body = created.json()
        self.assertTrue(body["secret_configured"])
        self.assertNotIn("secret", body)
        source_id = body["id"]
        updated_payload = {**payload,"name":"Updated RBAC source"}
        updated_payload.pop("secret")
        updated = await self.client.put(f"/api/v1/operations/sources/{source_id}",json=updated_payload,**self.auth("admin",csrf=True))
        self.assertEqual(updated.status_code,200,updated.text)
        self.assertTrue(updated.json()["secret_configured"])
        invalid = await self.client.put(f"/api/v1/operations/sources/{source_id}",json={**updated_payload,"base_url":"http://127.0.0.1/private"},**self.auth("admin",csrf=True))
        self.assertEqual(invalid.status_code,422)
        with (
            patch.dict(os.environ,{"SOURCE_SECRET_ENCRYPTION_KEY":"integration-only-encryption-key-123456789"}),
            patch("app.api.routes.operations.provider_manager.fetch",AsyncMock(return_value=(200,{}))),
            patch("app.api.routes.operations.require_public_destination",AsyncMock()),
        ):
            tested = await self.client.post(f"/api/v1/operations/sources/{source_id}/test",**self.auth("admin",csrf=True))
        self.assertEqual(tested.status_code,200,tested.text)
        self.assertTrue(tested.json()["ok"])
        toggled = await self.client.patch(f"/api/v1/operations/sources/{source_id}?enabled=false", **self.auth("admin", csrf=True))
        self.assertEqual(toggled.status_code, 200, toggled.text)
        async with pool.connection() as connection:
            stored = await connection.execute("SELECT secret_ciphertext::text AS encrypted FROM core.data_sources WHERE id=%s",(source_id,))
            self.assertNotIn(payload["secret"],(await stored.fetchone())["encrypted"])
            audit = await connection.execute("SELECT details FROM core.audit_log WHERE action='sources.create' AND target_id=%s ORDER BY id DESC LIMIT 1",(str(source_id),))
            details = (await audit.fetchone())["details"]
        self.assertNotIn("secret", str(details).lower())


if __name__ == "__main__":
    unittest.main()
