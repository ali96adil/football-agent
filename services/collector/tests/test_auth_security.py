from __future__ import annotations

import unittest
from unittest.mock import patch

from app.auth import ROLE_PERMISSIONS
from app.security import hash_password, hash_secret, verify_password


class AuthSecurityTests(unittest.TestCase):
    def test_password_hash_is_salted_and_verifiable(self) -> None:
        password = "correct horse battery staple"
        first = hash_password(password)
        second = hash_password(password)
        self.assertNotEqual(first, second)
        self.assertNotIn(password, first)
        self.assertTrue(verify_password(password, first))
        self.assertFalse(verify_password("incorrect password", first))

    def test_short_password_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "12"):
            hash_password("too-short")

    def test_session_hash_does_not_store_raw_token(self) -> None:
        self.assertEqual(len(hash_secret("session-token")), 64)
        self.assertNotIn("session-token", hash_secret("session-token"))

    def test_role_permission_matrix(self) -> None:
        self.assertEqual(ROLE_PERMISSIONS["viewer"], {"read"})
        self.assertEqual(ROLE_PERMISSIONS["operator"], {"read", "operate"})
        self.assertEqual(ROLE_PERMISSIONS["admin"], {"read", "operate", "admin"})


if __name__ == "__main__":
    unittest.main()
