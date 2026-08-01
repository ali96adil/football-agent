from __future__ import annotations

import unittest

from fastapi import HTTPException

from app.job_errors import JobExecutionError, safe_failure


class SafeJobFailureTests(unittest.TestCase):
    def test_http_auth_rate_limit_and_disabled_are_classified(self) -> None:
        self.assertEqual(safe_failure(HTTPException(401,"secret body"))["reason"],"authentication_failure")
        self.assertEqual(safe_failure(HTTPException(429,"quota"))["reason"],"rate_limit")
        self.assertEqual(safe_failure(HTTPException(409,"source disabled"))["reason"],"source_disabled")

    def test_technical_message_is_not_returned(self) -> None:
        result=safe_failure(RuntimeError("postgresql://user:password@db/private"))
        self.assertNotIn("password",str(result))

    def test_pipeline_failure_preserves_safe_stage_only(self) -> None:
        self.assertEqual(
            safe_failure(JobExecutionError("http_status",stage="competitions, fixtures")),
            {"reason":"http_status","stage":"competitions, fixtures"},
        )


if __name__ == "__main__": unittest.main()
