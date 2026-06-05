from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

_STORE_ROOT = Path(__file__).resolve().parents[3] / "store"
if str(_STORE_ROOT) not in sys.path:
    sys.path.insert(0, str(_STORE_ROOT))

from arcadia_store import StoreConfig, build_store, run_migrations

logger = logging.getLogger(__name__)


def _card_row(card, run_id: str, now_ms: int) -> dict:
    d = card.to_dict()
    traj = d.get("trajectory") or {}
    judge = d.get("judge") or {}
    return {
        "scenario_id": d["scenario_id"],
        "sweep_id": d["sweep_id"],
        "run_id": run_id,
        "task_id": d["task_id"],
        "surface": d["surface"],
        "model": d["model"],
        "seed": int(d["seed"]),
        "passed_gates": bool(d["passed_gates"]),
        "composite": float(d["composite"]),
        "failure_modes": d.get("failure_modes") or [],
        "error": d.get("error"),
        "tokens": int((traj.get("tokens_in") or 0) + (traj.get("tokens_out") or 0)),
        "cost_usd": traj.get("cost_usd"),
        "judge_weighted": judge.get("weighted"),
        "card_json": d,
        "created_at_ms": now_ms,
    }


async def index_scorecard(card, run_id: str) -> None:
    """Write a scorecard through to the store, if DATABASE_URL is configured.

    Args:
        card (ScoreCard): The computed scorecard.
        run_id (str): The per-run directory name used as the run identifier.
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return
    try:
        await run_migrations(dsn)
        store = build_store(StoreConfig(dsn=dsn))
        await store.init()
        try:
            await store.upsert_scorecard(
                _card_row(card, run_id, int(time.time() * 1000)))
        finally:
            await store.close()
    except Exception:
        logger.exception("scorecard indexing failed for %s", run_id)


async def index_sweep_aggregate(scenario: str, sweep_id: str,
                                aggregate: dict) -> None:
    """Write a sweep aggregate through to the store, if DATABASE_URL is set.

    Args:
        scenario (str): Scenario id.
        sweep_id (str): Sweep id.
        aggregate (dict): The aggregate report as a dict.
    """
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return
    agg = dict(aggregate)
    agg.setdefault("created_at_ms", int(time.time() * 1000))
    try:
        await run_migrations(dsn)
        store = build_store(StoreConfig(dsn=dsn))
        await store.init()
        try:
            await store.upsert_sweep_aggregate(scenario, sweep_id, agg)
        finally:
            await store.close()
    except Exception:
        logger.exception("sweep aggregate indexing failed for %s/%s",
                         scenario, sweep_id)
