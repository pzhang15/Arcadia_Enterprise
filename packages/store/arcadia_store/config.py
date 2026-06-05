from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StoreConfig:
    """Configuration for the persistence store.

    Args:
        dsn (str): SQLAlchemy async DSN, e.g. ``sqlite+aiosqlite:///path/arcadia.db``
            or ``postgresql+asyncpg://user:pw@host:5432/db``.
        flush_interval_seconds (float): How often the background flusher drains the buffer.
        event_buffer_capacity (int): Max buffered AG-UI/derived rows before oldest are dropped.
        stream_buffer_capacity (int): Max buffered relay stream rows before oldest are dropped.
        stream_retention_max (int): Keep at most this many newest stream_events rows when pruning.
        event_retention_days (int): Prune agui_events older than this many days.
        echo (bool): Echo SQL for debugging.
    """

    dsn: str
    flush_interval_seconds: float = 2.0
    event_buffer_capacity: int = 50_000
    stream_buffer_capacity: int = 100_000
    stream_retention_max: int = 200_000
    event_retention_days: int = 30
    echo: bool = False
