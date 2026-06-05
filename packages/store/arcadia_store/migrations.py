from __future__ import annotations

import logging

from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from arcadia_store.models import metadata

logger = logging.getLogger(__name__)


def _create_all(sync_conn: Connection) -> None:
    metadata.create_all(sync_conn, checkfirst=True)


async def run_migrations(dsn: str) -> None:
    """Provision the schema for the given DSN (idempotent, dialect-aware).

    Uses SQLAlchemy ``create_all`` via an async ``run_sync`` so it works on both
    Postgres and SQLite without a separate sync driver and without nesting an
    event loop. This is the extension point for a future migration tool.

    Args:
        dsn (str): SQLAlchemy async DSN.
    """
    engine = create_async_engine(dsn)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(_create_all)
    finally:
        await engine.dispose()
