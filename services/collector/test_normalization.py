import asyncio
from psycopg.types.json import Jsonb
from app.db.connection import pool
from app.normalizers.api_football_mapper import (
    map_api_football_fixture,
)
from app.services.normalization_service import NormalizationService


RAW_PAYLOAD_ID = 91
SOURCE_ID = 2


async def main():
    await pool.open()
    await pool.wait()

    try:
        async with pool.connection() as connection:

            result = await connection.execute(
                """
                SELECT payload
                FROM raw.api_payloads
                WHERE id = %s
                """,
                (RAW_PAYLOAD_ID,),
            )

            row = await result.fetchone()

            if row is None:
                raise RuntimeError("Raw payload not found")

            payload = row["payload"]

            fixture = map_api_football_fixture(
                payload["response"][0]
            )

            service = NormalizationService()

            fixture_id = await service.normalize_fixture(
                connection,
                fixture=fixture,
                source_id=SOURCE_ID,
                raw_payload_id=RAW_PAYLOAD_ID,
                payload_hash=None,
            )

            print()
            print("Normalization succeeded")
            print("Fixture ID:", fixture_id)

    finally:
        await pool.close()


asyncio.run(main())