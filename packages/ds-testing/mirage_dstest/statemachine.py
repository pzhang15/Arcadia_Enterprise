"""Async-capable Hypothesis ``RuleBasedStateMachine`` spine.

This module provides :class:`DSStateMachine`, a synchronous Hypothesis state
machine that owns a SINGLE persistent asyncio event loop for the lifetime of
one example. Every loop-affine object (``Workspace``, forked children,
``asyncio.Lock`` instances, ...) must be created inside that one loop via
:meth:`DSStateMachine.setup_async` and driven through
:meth:`DSStateMachine._run`. Keeping a single loop is what makes
``asyncio.Lock``/``Future`` identity coherent across all rules of one example;
spinning up a fresh ``asyncio.run`` per rule would attach futures to a
different loop and break.

Hard rules enforced here:
  * The machine is SYNC. Never decorate it with ``@pytest.mark.asyncio``.
  * Exactly one loop is created in ``__init__`` via
    ``asyncio.new_event_loop()`` + ``asyncio.set_event_loop`` and reused for
    every rule and for teardown.
  * Every rule body runs through ``self._run(coro)`` which is
    ``loop.run_until_complete`` on THE one loop.
  * ``asyncio.run`` is never called inside a rule.
  * ``loop.close()`` always runs in :meth:`teardown` (try/finally) after
    :meth:`teardown_async`.

This module does NOT import mirage. The clock/RNG dependencies are injected
deterministically; no wall-clock time and no unseeded randomness are used.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

import asyncio
import os
import warnings

from hypothesis import HealthCheck, settings
from hypothesis.stateful import RuleBasedStateMachine, run_state_machine_as_test

from mirage_dstest.clock import VirtualClock
from mirage_dstest.rng import SeededRandom, seed_from_env

if TYPE_CHECKING:
    from collections.abc import Coroutine

T = TypeVar("T")

_STATE_MACHINE_SETTINGS = settings(
    deadline=None,
    suppress_health_check=list(HealthCheck),
)


class DSStateMachine(RuleBasedStateMachine):
    """Synchronous Hypothesis state machine over a single persistent loop.

    Subclasses add ``@rule`` / ``@invariant`` methods whose bodies call
    ``self._run(some_coro())``. They override :meth:`setup_async` to build
    loop-affine objects (e.g. a mirage ``Workspace``) and
    :meth:`teardown_async` to close them. The base owns the loop, the
    :class:`VirtualClock`, the :class:`SeededRandom`, and deterministic
    teardown.

    Attributes:
        clock (VirtualClock): Deterministic logical clock for this example.
        rng (SeededRandom): Replay-stable RNG seeded from ``DST_SEED``.
    """

    clock: VirtualClock
    rng: SeededRandom

    TestCase: type  # populated by Hypothesis on subclasses; declared for typing

    Settings = _STATE_MACHINE_SETTINGS

    def __init__(self) -> None:
        """Create the single owned loop and build the clock + RNG.

        A fresh event loop is created and installed as the current loop for
        this thread, then ``setup_async`` is driven on it so every loop-affine
        object is bound to THIS loop. The RNG seed is read from ``DST_SEED``
        (falling back to a fixed default) so replay is deterministic; the
        clock starts at logical time ``0.0``.

        Determinism / leak safety: if ``setup_async`` raises (e.g. a failing
        Hypothesis example whose setup blows up), the owned loop is closed and
        the thread-default loop is restored to whatever it was before this
        constructor ran (or cleared). Otherwise a failed example would leak the
        loop and its file descriptors, and would leave a closed loop installed
        as the thread default for the next example.
        """
        super().__init__()
        self._previous_loop = _safe_get_event_loop()
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop_closed = False
        seed = seed_from_env(default_factory=_default_seed)
        self.rng = SeededRandom(seed)
        self.clock = VirtualClock()
        try:
            self._run(self.setup_async())
        except BaseException:
            self._loop.close()
            self._loop_closed = True
            asyncio.set_event_loop(self._previous_loop)
            raise

    def _run(self, coro: "Coroutine[Any, Any, T]") -> "T":
        """Drive a coroutine to completion on THE one owned loop.

        Args:
            coro (Coroutine[Any, Any, T]): The coroutine to run. It must only
                touch objects affine to this machine's loop (anything built in
                :meth:`setup_async`).

        Returns:
            T: The coroutine's result.

        Raises:
            RuntimeError: If the owned loop has already been closed (i.e.
                ``_run`` was called after :meth:`teardown`).
        """
        if self._loop_closed:
            raise RuntimeError("DSStateMachine loop is closed; cannot run coroutine")
        return self._loop.run_until_complete(coro)

    async def setup_async(self) -> None:
        """Build loop-affine objects for this example.

        Override in subclasses to construct objects that must live on the
        machine's single loop (e.g. ``self.ws = Workspace(...)`` or an initial
        forked workspace). Runs once, inside ``__init__``, on the owned loop.
        The base implementation does nothing.
        """

    async def teardown_async(self) -> None:
        """Tear down loop-affine objects for this example.

        Override in subclasses to close objects built in
        :meth:`setup_async` (e.g. ``await self.ws.close()``). Runs once, on the
        owned loop, immediately before the loop is closed. The base
        implementation does nothing.
        """

    def teardown(self) -> None:
        """Run async teardown then close the owned loop (always).

        Hypothesis calls this after each example. :meth:`teardown_async` is
        driven on the owned loop, and ``loop.close()`` runs in a ``finally`` so
        the loop is always closed even if teardown raises. After this call the
        loop is closed and :meth:`_run` will refuse to run further coroutines.
        """
        if self._loop_closed:
            return
        try:
            self._loop.run_until_complete(self.teardown_async())
        finally:
            self._loop.close()
            self._loop_closed = True
            asyncio.set_event_loop(self._previous_loop)


def _safe_get_event_loop() -> "asyncio.AbstractEventLoop | None":
    """Return the current thread's event loop without raising or warning.

    On Python 3.12 ``asyncio.get_event_loop`` raises ``RuntimeError`` (and
    ``get_event_loop_policy().get_event_loop()`` emits a ``DeprecationWarning``)
    when no loop is set; both are suppressed here so this returns ``None`` in
    that case. The state machine uses the result only to restore the prior
    thread-default loop after it owns and closes its own loop.

    Returns:
        asyncio.AbstractEventLoop | None: The installed loop, or None when
        none is set for this thread.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        try:
            return asyncio.get_event_loop_policy().get_event_loop()
        except RuntimeError:
            return None


def _default_seed() -> int:
    """Return the fixed default seed used when ``DST_SEED`` is unset.

    This is intentionally a constant (never time- or entropy-derived) so the
    harness is deterministic by default; callers wanting a different fixed seed
    set ``DST_SEED`` in the environment.

    Returns:
        int: The default seed value.
    """
    return 0


def run_machine(
    machine_cls: "type[DSStateMachine]",
    *,
    seed: int | None = None,
    max_examples: int = 200,
    stateful_step_count: int = 80,
) -> None:
    """Run a :class:`DSStateMachine` as a Hypothesis stateful test.

    Thin wrapper over ``run_state_machine_as_test`` that re-asserts the
    load-bearing settings (``deadline=None`` and all ``HealthCheck`` suppressed)
    even though :attr:`DSStateMachine.Settings` already sets them, in case a
    custom ``machine_cls.Settings`` was supplied. When ``seed`` is given it is
    exported via the ``DST_SEED`` environment variable (so the machine's
    ``__init__`` and any derived sub-streams pick it up) and Hypothesis is run
    in ``derandomize`` mode for reproducible example generation.

    Args:
        machine_cls (type[DSStateMachine]): The state-machine subclass to run.
        seed (int | None): Optional fixed seed. When provided it is written to
            ``DST_SEED`` for the duration of the run and Hypothesis is
            derandomized. When ``None`` the machine reads whatever ``DST_SEED``
            is already in the environment (or its default).
        max_examples (int): Number of examples Hypothesis generates.
        stateful_step_count (int): Max number of rule invocations per example.

    Returns:
        None
    """
    derandomize = seed is not None
    run_settings = settings(
        deadline=None,
        suppress_health_check=list(HealthCheck),
        max_examples=max_examples,
        stateful_step_count=stateful_step_count,
        derandomize=derandomize,
    )
    if seed is None:
        run_state_machine_as_test(machine_cls, settings=run_settings)
        return
    previous = os.environ.get("DST_SEED")
    os.environ["DST_SEED"] = str(seed)
    try:
        run_state_machine_as_test(machine_cls, settings=run_settings)
    finally:
        if previous is None:
            os.environ.pop("DST_SEED", None)
        else:
            os.environ["DST_SEED"] = previous


def register_profiles() -> None:
    """Register the ``dev`` / ``ci`` / ``debug`` Hypothesis settings profiles.

    Profiles are selected at runtime via the ``HYPOTHESIS_PROFILE`` env var (or
    ``settings.load_profile``). All profiles disable the deadline and suppress
    every ``HealthCheck`` (the stateful machine drives a real loop per example,
    which trips the default timing/data-generation health checks). The
    profiles differ only in breadth:

      * ``dev``  — fast local iteration (fewer examples / shorter step count).
      * ``ci``   — thorough, the default gate (more examples / longer chains).
      * ``debug``— minimal + verbose for reproducing a single failing example.

    Returns:
        None
    """
    common: dict[str, Any] = {
        "deadline": None,
        "suppress_health_check": list(HealthCheck),
    }
    settings.register_profile(
        "dev",
        max_examples=25,
        stateful_step_count=40,
        **common,
    )
    settings.register_profile(
        "ci",
        max_examples=200,
        stateful_step_count=80,
        **common,
    )
    settings.register_profile(
        "debug",
        max_examples=10,
        stateful_step_count=20,
        print_blob=True,
        **common,
    )
