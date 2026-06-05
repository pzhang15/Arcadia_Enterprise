from arcadia_store import StoreConfig, build_store
from mirage_eval.report.store_index import index_scorecard


class _FakeCard:
    def to_dict(self):
        return {
            "scenario_id": "northhill_corp",
            "task_id": "triage",
            "surface": "l1",
            "model": "gpt-test",
            "seed": 1,
            "sweep_id": "sweep-abc",
            "passed_gates": True,
            "composite": 0.83,
            "trajectory": {"tokens_in": 100, "tokens_out": 40, "cost_usd": 0.02},
            "judge": {"weighted": 0.75},
            "failure_modes": [],
            "error": None,
        }


async def test_index_scorecard_writes_through(tmp_path, monkeypatch):
    dsn = f"sqlite+aiosqlite:///{tmp_path}/eval.db"
    monkeypatch.setenv("DATABASE_URL", dsn)
    await index_scorecard(_FakeCard(), "triage__gpt-test__seed1__l1")

    store = build_store(StoreConfig(dsn=dsn))
    await store.init()
    try:
        card = await store.get_scorecard(
            "northhill_corp", "sweep-abc", "triage__gpt-test__seed1__l1")
        assert card is not None
        assert card["composite"] == 0.83
        assert {"scenario": "northhill_corp",
                "sweep_id": "sweep-abc"} in await store.list_sweeps()
    finally:
        await store.close()


async def test_index_scorecard_noop_without_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Should be a silent no-op, not raise.
    await index_scorecard(_FakeCard(), "run-x")
