from __future__ import annotations

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


async def open_connection_pool() -> None:
    """
    Opens the shared PostgreSQL connection pool.
    Safe to call multiple times.
    """
    if pool.closed:
        await pool.open()

    await pool.wait()


async def close_connection_pool() -> None:
    """
    Closes the shared PostgreSQL connection pool.
    """
    if not pool.closed:
        await pool.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await open_connection_pool()

    try:
        yield

    finally:
        await close_connection_pool()