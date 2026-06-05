from __future__ import annotations

import sys
from pathlib import Path

import pytest_asyncio

_PKG_DIR = Path(__file__).resolve().parent.parent
if str(_PKG_DIR) not in sys.path:
    sys.path.insert(0, str(_PKG_DIR))

from arcadia_store import (StoreConfig, build_store,  # noqa: E402
                           run_migrations)


@pytest_asyncio.fixture
async def store(tmp_path):
    dsn = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    await run_migrations(dsn)
    s = build_store(StoreConfig(dsn=dsn, flush_interval_seconds=0.05))
    await s.init()
    yield s
    await s.close()
