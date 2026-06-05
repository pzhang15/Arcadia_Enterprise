"""Unit tests for the deterministic VirtualClock."""

from __future__ import annotations

import time

import pytest

from mirage_dstest.clock import VirtualClock


def test_starts_at_origin_and_elapsed_zero() -> None:
    clock = VirtualClock(start=5.0)
    assert clock.now() == 5.0
    assert clock.monotonic() == 5.0
    assert clock.elapsed == 0.0


def test_advance_is_monotonic_and_pure() -> None:
    clock = VirtualClock()
    clock.advance(1.5)
    clock.advance(0.5)
    assert clock.now() == 2.0
    assert clock.elapsed == 2.0


def test_advance_rejects_negative() -> None:
    clock = VirtualClock()
    with pytest.raises(ValueError):
        clock.advance(-1.0)


def test_advance_to_rejects_backward() -> None:
    clock = VirtualClock()
    clock.advance_to(3.0)
    assert clock.now() == 3.0
    with pytest.raises(ValueError):
        clock.advance_to(2.9)


async def test_sim_sleep_advances_without_real_delay() -> None:
    clock = VirtualClock()
    wall_start = time.monotonic()
    await clock.sim_sleep(100.0)
    wall_elapsed = time.monotonic() - wall_start
    assert clock.now() == 100.0
    assert wall_elapsed < 0.5


async def test_sim_sleep_rejects_negative() -> None:
    clock = VirtualClock()
    with pytest.raises(ValueError):
        await clock.sim_sleep(-0.001)


def test_two_clocks_same_advances_are_identical() -> None:
    a = VirtualClock()
    b = VirtualClock()
    for dt in (0.1, 0.2, 0.3, 10.0):
        a.advance(dt)
        b.advance(dt)
    assert a.now() == b.now()
