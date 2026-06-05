"""Unit tests for the replay-stable SeededRandom."""

from __future__ import annotations

import pytest

from mirage_dstest.rng import SeededRandom, seed_from_env


def test_master_stream_replays_from_seed() -> None:
    a = SeededRandom(1234)
    b = SeededRandom(1234)
    assert [a.random() for _ in range(8)] == [b.random() for _ in range(8)]
    assert [a.randint(0, 99) for _ in range(8)] == [
        b.randint(0, 99) for _ in range(8)
    ]


def test_derive_unit_is_pure_in_coordinates() -> None:
    rng = SeededRandom(42)
    first = rng.derive_unit(op_index=3, site="s", key="/a.txt")
    second = rng.derive_unit(op_index=3, site="s", key="/a.txt")
    assert first == second
    assert 0.0 <= first < 1.0


def test_derive_unit_is_order_independent() -> None:
    rng = SeededRandom(7)
    direct = rng.derive_unit(op_index=10, site="x", key="k")
    rng.random()
    rng.random()
    rng.getrandbits(16)
    after_master_advance = rng.derive_unit(op_index=10, site="x", key="k")
    assert direct == after_master_advance


def test_derive_unit_distinct_coordinates_differ() -> None:
    rng = SeededRandom(99)
    a = rng.derive_unit(op_index=0, site="s", key="k")
    b = rng.derive_unit(op_index=1, site="s", key="k")
    c = rng.derive_unit(op_index=0, site="t", key="k")
    d = rng.derive_unit(op_index=0, site="s", key="j")
    assert len({a, b, c, d}) == 4


def test_derive_int_in_range_and_pure() -> None:
    rng = SeededRandom(5)
    for i in range(50):
        v = rng.derive_int(op_index=i, site="s", key=f"/k{i}", bound=8)
        assert 0 <= v < 8
    again = rng.derive_int(op_index=10, site="s", key="/k10", bound=8)
    once = SeededRandom(5).derive_int(op_index=10, site="s", key="/k10", bound=8)
    assert again == once


def test_derive_int_rejects_bad_bound() -> None:
    rng = SeededRandom(0)
    with pytest.raises(ValueError):
        rng.derive_int(op_index=0, site="s", key="k", bound=0)


def test_fork_child_deterministic_and_label_scoped() -> None:
    parent = SeededRandom(2024)
    a1 = parent.fork_child("alpha")
    a2 = SeededRandom(2024).fork_child("alpha")
    b = parent.fork_child("beta")
    assert a1.seed == a2.seed
    assert a1.seed != b.seed


def test_seed_from_env_reads_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DST_SEED", "0x10")
    assert seed_from_env() == 16


def test_seed_from_env_raises_without_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DST_SEED", raising=False)
    with pytest.raises(RuntimeError):
        seed_from_env()


def test_seed_from_env_uses_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DST_SEED", raising=False)
    assert seed_from_env(default_factory=lambda: 77) == 77
