"""Deterministic simulated time authority for the mirage_dstest harness.

VirtualClock is a monotonic, simulated time source that NEVER reads the
wall clock. Time advances only when something explicitly moves it forward:
either a direct ``advance``/``advance_to`` call, or an awaitable
``sim_sleep`` that records a logical wake by bumping the clock instead of
blocking. This makes every fault ordering and timestamp in the harness a
pure function of the sequence of advances, which is the precondition for
seed-based replay.

The design is injected, not loop-patched (cf. FoundationDB Sim2 / looptime):
the clock is passed explicitly to whatever needs a time source rather than
monkeypatching the running event loop. This deliberately avoids reaching
into CPython-private asyncio internals (``loop._scheduled`` / ``_run_once``),
which are version-fragile.

EXPLICIT LIMITATION: VirtualClock governs the harness's LOGICAL time and
fault ordering ONLY. It is NOT the asyncio event loop's clock. In
particular it does not override ``loop.time()``, so it does NOT
fast-forward real timers such as ``asyncio.wait_for(..., timeout=...)`` or
``loop.call_later`` — those still observe true wall time. Tests must build
their timeouts on this clock (e.g. compare against ``now()`` /
``sim_sleep``) rather than relying on asyncio's own timeout machinery to be
sped up.
"""

from __future__ import annotations

import asyncio


class VirtualClock:
    """Monotonic simulated clock whose time only advances explicitly.

    The clock starts at ``start`` and exposes the elapsed simulated seconds
    since construction via :attr:`elapsed`. It is single-threaded by
    assumption (the harness runs everything on one asyncio loop), so the
    advance operations need no locking.
    """

    def __init__(self, *, start: float = 0.0) -> None:
        """Initialize the clock.

        Args:
            start (float): The initial simulated time in seconds. Defaults
                to ``0.0``. May be negative; ``elapsed`` is always measured
                relative to this origin.
        """
        self._start: float = float(start)
        self._now: float = float(start)

    def now(self) -> float:
        """Return the current simulated time.

        Returns:
            float: The current simulated time in seconds.
        """
        return self._now

    def monotonic(self) -> float:
        """Return the current simulated time (alias for :meth:`now`).

        Provided so the clock can be dropped in wherever a
        ``time.monotonic``-style callable is expected for injection.

        Returns:
            float: The current simulated time in seconds.
        """
        return self._now

    def advance(self, dt: float) -> None:
        """Advance the simulated time forward by ``dt`` seconds.

        Args:
            dt (float): A non-negative number of seconds to advance. A
                negative value raises ``ValueError`` (the clock never moves
                backward and never silently clamps).

        Raises:
            ValueError: If ``dt`` is negative.
        """
        if dt < 0:
            raise ValueError(f"VirtualClock.advance requires dt >= 0, got {dt!r}")
        self._now += float(dt)

    def advance_to(self, t: float) -> None:
        """Advance the simulated time forward to the absolute time ``t``.

        Args:
            t (float): An absolute simulated time in seconds that must be at
                or after the current time. A value earlier than
                :meth:`now` raises ``ValueError`` (no backward movement, no
                silent clamp).

        Raises:
            ValueError: If ``t`` is earlier than the current simulated time.
        """
        if t < self._now:
            raise ValueError(
                f"VirtualClock.advance_to requires t >= now ({self._now!r}), got {t!r}"
            )
        self._now = float(t)

    async def sim_sleep(self, dt: float) -> None:
        """Logically sleep for ``dt`` seconds without any real delay.

        Yields control to the event loop exactly once via
        ``asyncio.sleep(0)`` so other ready coroutines can interleave, then
        advances the simulated clock by ``dt``. It NEVER calls
        ``asyncio.sleep(dt)`` — no real wall-clock time elapses regardless
        of how large ``dt`` is.

        Args:
            dt (float): A non-negative number of simulated seconds to sleep.
                A negative value raises ``ValueError`` (no silent clamp).

        Raises:
            ValueError: If ``dt`` is negative.
        """
        if dt < 0:
            raise ValueError(f"VirtualClock.sim_sleep requires dt >= 0, got {dt!r}")
        await asyncio.sleep(0)
        self._now += float(dt)

    @property
    def elapsed(self) -> float:
        """Return the simulated seconds elapsed since construction.

        Returns:
            float: ``now() - start``, the total simulated time advanced
            since the clock was created.
        """
        return self._now - self._start
