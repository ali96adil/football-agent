from typing import Any


class DashboardRepository:
    async def get_dashboard_stats(
        self,
        connection: Any,
    ) -> dict:
        query = """
        SELECT
            (SELECT COUNT(*) FROM core.fixtures) AS fixtures,

            (SELECT COUNT(*) FROM core.teams) AS teams,

            (SELECT COUNT(*) FROM core.competitions) AS competitions,

            (SELECT COUNT(*) FROM core.match_predictions) AS predictions,

            (
                SELECT COUNT(*)
                FROM core.fixtures
                WHERE fixture_status='scheduled'
            ) AS scheduled,

            (
                SELECT COUNT(*)
                FROM core.fixtures
                WHERE fixture_status='live'
            ) AS live,

            (
                SELECT COUNT(*)
                FROM core.fixtures
                WHERE result_confirmed = TRUE
            ) AS finished;
        """

        result = await connection.execute(query)

        row = await result.fetchone()

        return {
            "fixtures": int(row["fixtures"]),
            "teams": int(row["teams"]),
            "competitions": int(row["competitions"]),
            "predictions": int(row["predictions"]),
            "scheduled": int(row["scheduled"]),
            "live": int(row["live"]),
            "finished": int(row["finished"]),
        }

    async def get_operations(self, connection: Any) -> dict:
        sources_result = await connection.execute(
            """
            SELECT code, name, enabled, last_success_at, last_failure_at,
                   requests_used_today, updated_at
              FROM core.data_sources
             ORDER BY priority DESC, code
            """
        )
        sources = await sources_result.fetchall()

        worker_result = await connection.execute(
            """
            SELECT worker_id, status, heartbeat_at, current_job_id,
                   scheduler_enabled, schedule_interval_seconds,
                   next_sync_at, started_at
              FROM core.worker_heartbeats
             ORDER BY heartbeat_at DESC
             LIMIT 1
            """
        )
        worker = await worker_result.fetchone()

        jobs_result = await connection.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE status IN ('queued', 'retry')) AS pending,
                COUNT(*) FILTER (WHERE status = 'running') AS running,
                COUNT(*) FILTER (WHERE status = 'dead_letter') AS dead_letter,
                MAX(finished_at) FILTER (
                    WHERE job_type = 'sync_pipeline' AND status = 'succeeded'
                ) AS last_sync_at,
                MAX(finished_at) FILTER (
                    WHERE job_type = 'sync_pipeline' AND status = 'dead_letter'
                ) AS last_sync_failure_at
            FROM core.jobs
            """
        )
        jobs = await jobs_result.fetchone()

        payload_result = await connection.execute(
            """
            SELECT MAX(requested_at) FILTER (WHERE response_status < 400) AS last_data_update_at
              FROM raw.api_payloads
            """
        )
        payload = await payload_result.fetchone()

        return {
            "sources": sources,
            "worker": worker,
            "jobs": {
                "pending": int(jobs["pending"]),
                "running": int(jobs["running"]),
                "dead_letter": int(jobs["dead_letter"]),
                "last_sync_at": jobs["last_sync_at"],
                "last_sync_failure_at": jobs["last_sync_failure_at"],
            },
            "last_data_update_at": payload["last_data_update_at"],
        }
