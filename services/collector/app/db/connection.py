from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import build_database_url


pool = AsyncConnectionPool(
    conninfo=build_database_url(),
    min_size=1,
    max_size=5,
    open=False,
    kwargs={
        "row_factory": dict_row,
    },
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await pool.open()
    await pool.wait()

    try:
        yield
    finally:
        await pool.close()