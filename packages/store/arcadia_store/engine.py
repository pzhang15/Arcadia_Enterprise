from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine

from arcadia_store.config import StoreConfig
from arcadia_store.sql_store import SqlStore


def _set_sqlite_pragma(dbapi_conn, _record) -> None:
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def build_store(config: StoreConfig) -> SqlStore:
    """Build a SqlStore from configuration, wiring SQLite PRAGMAs when needed.

    Args:
        config (StoreConfig): Store configuration including the DSN.

    Returns:
        SqlStore: A ready-to-init store (call ``await store.init()``).
    """
    engine = create_async_engine(config.dsn, echo=config.echo)
    if config.dsn.startswith("sqlite"):
        event.listen(engine.sync_engine, "connect", _set_sqlite_pragma)
    return SqlStore(engine, config)
