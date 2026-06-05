"""Deterministic, seed-driven fault injection for the mirage Resource surface.

ChaosResource is a transparent wrapper that quacks like a mirage resource: it
forwards the exact async op signatures (read_bytes / write / readdir / stat /
unlink / read_stream / append / fingerprint) to an inner backend, but gates each
op-site on a per-decision derived random draw before forwarding. Every decision
(fired or not) is appended to a replayable log on the FaultSchedule.

Determinism contract (scope: SERIAL single-op driving):
    Each per-op decision is drawn with ``rng.derive_unit(op_index, site, key)`` —
    a pure function of (seed, op_index, site, path_key) — NOT a shared mutable
    generator. A single monotonic op-index counter lives on the ChaosResource and
    is incremented once per op-site entry (atomic under single-threaded asyncio).
    The DRAW VALUE for a given op-index is independent of the master RNG's
    advance-order; what is NOT interleaving-invariant is the op-index ASSIGNMENT
    itself: ``op_index`` is handed out in the wall-order op-sites enter
    ``_next_decision``. The replay guarantee therefore holds when one
    ChaosResource is driven SERIALLY — one op-site entered, awaited to
    completion, before the next — which is exactly how ``DSStateMachine._run``
    drives it (each rule runs one op to completion on the single loop). Under
    that serial discipline the op-index sequence is fixed by program order and
    the fired faults replay byte-for-byte from the seed alone. Concurrent
    op-sites racing into one shared ChaosResource (e.g. two ``asyncio.gather``ed
    writes through the same wrapper) could interleave their op-index assignment
    and are OUT OF SCOPE for replay: do NOT share a single ChaosResource across
    concurrently-driven op-sites; give each concurrent driver its own forked
    wrapper instead.

Replay scope:
    Replay covers WHICH faults fire and the resulting values/errors — NOT
    nanosecond wall-clock timing. The ``delay`` action advances the injected
    VirtualClock via ``sim_sleep`` (logical time only); it never calls a real
    sleep, so two runs of the same seed are timing-identical in logical time and
    near-instant in wall time.

Fault menu:
    off           no-op; forward unchanged.
    delay         await clock.sim_sleep(d) then forward (logical delay only).
    drop          raise SimulatedFault BEFORE the op runs (effect never lands).
    dup           forward the op twice (at-least-once duplication).
    partial       for a write, commit k<n of n chunks then raise SimulatedFault.
    lost_ack      forward the FULL write, THEN raise SimulatedLostAck (Helland
                  closing-stage ambiguity: the effect landed but the ack is lost).
    drift         mutate the fingerprint the caller observes (version drift).

Safety:
    The destructive actions (dup / partial / lost_ack) mutate observable state.
    They only fire when ``allow_destructive`` is True AND the inner resource is
    not remote (``inner.is_remote`` is False) — a ChaosResource never mutates a
    real remote/externally-owned backend.

Runtime mirage coupling lives in adapters.py (wrap_chaos), NOT here: this module
references mirage only through structural Protocols and imports cleanly with no
mirage installed.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from mirage_dstest.clock import VirtualClock
from mirage_dstest.protocols import PathSpecLike, ResourceLike
from mirage_dstest.rng import SeededRandom


class FaultAction(str, Enum):
    OFF = "off"
    DELAY = "delay"
    DROP = "drop"
    DUPLICATE = "dup"
    PARTIAL = "partial"
    LOST_ACK = "lost_ack"
    VERSION_DRIFT = "drift"


DESTRUCTIVE_ACTIONS: frozenset[FaultAction] = frozenset(
    {FaultAction.DUPLICATE, FaultAction.PARTIAL, FaultAction.LOST_ACK}
)


class SimulatedFault(Exception):
    """Base class for an injected, simulated backend fault.

    Raised for drop / partial / crash-style faults. Carries the originating op
    site and path so callers and the consistency checker can classify it.

    Args:
        message (str): Human-readable description of the injected fault.
        site (str | None): The op-site method name that was faulted.
        path_key (str | None): The normalized path key the op targeted.
    """

    def __init__(
        self,
        message: str,
        *,
        site: str | None = None,
        path_key: str | None = None,
    ) -> None:
        super().__init__(message)
        self.site = site
        self.path_key = path_key


class SimulatedLostAck(SimulatedFault):
    """A lost-acknowledgement fault: the effect landed but the ack was lost.

    Raised AFTER the wrapped write has been fully applied to the inner backend,
    modelling the Helland closing-stage ambiguity where the caller cannot tell
    whether the mutation took effect.
    """


@dataclass(frozen=True)
class FaultScope:
    method_glob: str = "*"
    path_glob: str = "*"
    op_index_range: tuple[int, int] | None = None

    def matches(self, *, site: str, path_key: str, op_index: int) -> bool:
        """Return True if this scope selects the given op-site.

        Args:
            site (str): The op-site method name (e.g. ``"read_bytes"``).
            path_key (str): The normalized path key of the op.
            op_index (int): The monotonic op index of the op.

        Returns:
            bool: True when method, path, and op-index window all match.
        """
        if not fnmatch.fnmatchcase(site, self.method_glob):
            return False
        if not fnmatch.fnmatchcase(path_key, self.path_glob):
            return False
        if self.op_index_range is not None:
            low, high = self.op_index_range
            if op_index < low or op_index > high:
                return False
        return True


@dataclass(frozen=True)
class FaultRule:
    action: FaultAction
    prob: float
    max_fires: int | None = None
    scope: FaultScope = field(default_factory=FaultScope)
    params: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.action, FaultAction):
            raise TypeError(f"action must be a FaultAction, got {self.action!r}")
        if not (0.0 <= self.prob <= 1.0):
            raise ValueError(
                f"prob must be in [0.0, 1.0], got {self.prob!r}"
            )
        if self.max_fires is not None and self.max_fires < 0:
            raise ValueError(
                f"max_fires must be >= 0 or None, got {self.max_fires!r}"
            )
        if self.action is FaultAction.PARTIAL:
            n = int(self.params.get("n", 0))
            k = int(self.params.get("k", 0))
            if n <= 0:
                raise ValueError("partial fault requires params['n'] >= 1")
            if not (0 <= k < n):
                raise ValueError(
                    "partial fault requires 0 <= params['k'] < params['n'] "
                    f"(got k={k}, n={n})"
                )
        if self.action is FaultAction.DELAY:
            d = float(self.params.get("delay", 0.0))
            if d < 0:
                raise ValueError("delay fault requires params['delay'] >= 0")


@dataclass(frozen=True)
class FaultDecision:
    op_index: int
    site: str
    path_key: str
    draw: float
    fired: bool
    action: FaultAction


_SEGMENT_RE = re.compile(
    r"""
    ^\s*
    (?:(?P<prob>\d+(?:\.\d+)?)\s*%\s*)?      # optional NN% or NN.N%
    (?:(?P<count>\d+)\s*\*\s*)?               # optional N* (max_fires budget)
    (?P<action>[A-Za-z_][A-Za-z_0-9]*)        # action keyword
    (?:\(\s*(?P<args>[^)]*)\s*\))?            # optional (args)
    \s*$
    """,
    re.VERBOSE,
)

_ACTION_ALIASES: dict[str, FaultAction] = {
    "off": FaultAction.OFF,
    "noop": FaultAction.OFF,
    "delay": FaultAction.DELAY,
    "latency": FaultAction.DELAY,
    "drop": FaultAction.DROP,
    "error": FaultAction.DROP,
    "dup": FaultAction.DUPLICATE,
    "duplicate": FaultAction.DUPLICATE,
    "partial": FaultAction.PARTIAL,
    "lost_ack": FaultAction.LOST_ACK,
    "lostack": FaultAction.LOST_ACK,
    "drift": FaultAction.VERSION_DRIFT,
    "version_drift": FaultAction.VERSION_DRIFT,
}


def _parse_args(action: FaultAction, raw: str | None) -> dict[str, Any]:
    """Parse a fail-rs argument list into a fault params mapping.

    Args:
        action (FaultAction): The action the args belong to.
        raw (str | None): The raw text inside the parentheses, or None.

    Returns:
        dict[str, Any]: The params mapping for the FaultRule.
    """
    tokens = [t.strip() for t in raw.split(",")] if raw else []
    tokens = [t for t in tokens if t != ""]
    if action is FaultAction.DELAY:
        if not tokens:
            return {"delay": 0.0}
        ms = float(tokens[0])
        return {"delay": ms / 1000.0}
    if action is FaultAction.PARTIAL:
        if len(tokens) >= 2:
            return {"k": int(tokens[0]), "n": int(tokens[1])}
        if len(tokens) == 1:
            return {"k": int(tokens[0]), "n": int(tokens[0]) + 1}
        return {"k": 1, "n": 2}
    if tokens:
        raise ValueError(
            f"action {action.value!r} does not accept arguments, got {raw!r}"
        )
    return {}


def _parse_segment(segment: str) -> FaultRule:
    """Parse one ``->``-delimited fail-rs segment into a FaultRule.

    Args:
        segment (str): A single segment, e.g. ``"20%3*delay(250)"``.

    Returns:
        FaultRule: The parsed rule.
    """
    match = _SEGMENT_RE.match(segment)
    if match is None:
        raise ValueError(f"invalid fault segment: {segment!r}")
    keyword = match.group("action").lower()
    action = _ACTION_ALIASES.get(keyword)
    if action is None:
        valid = ", ".join(sorted(_ACTION_ALIASES))
        raise ValueError(
            f"unknown fault action {keyword!r} (valid: {valid})"
        )
    prob_raw = match.group("prob")
    prob = float(prob_raw) / 100.0 if prob_raw is not None else 1.0
    if not (0.0 <= prob <= 1.0):
        raise ValueError(f"probability out of range in segment {segment!r}")
    count_raw = match.group("count")
    max_fires = int(count_raw) if count_raw is not None else None
    params = _parse_args(action, match.group("args"))
    return FaultRule(action=action, prob=prob, max_fires=max_fires, params=params)


class FaultSchedule:
    """An ordered set of fault rules plus a replayable decision log.

    The schedule evaluates rules in declaration order for each op-site. Each
    matching rule gets its own independent deterministic draw (derived from the
    seed and a per-rule key), so probabilities compose as independent fall-
    through stages (fail-rs ``->`` semantics): the first matching rule that both
    passes its probability gate and has remaining budget fires; otherwise the
    next matching rule is tried. Every evaluated op-site produces exactly one
    FaultDecision appended to the history.

    Args:
        rng (SeededRandom): The seeded RNG providing derived per-decision draws.
        rules (Sequence[FaultRule]): Ordered fault rules.
        allow_destructive (bool): Gate for state-mutating faults (dup / partial /
            lost_ack). When False those actions are recorded as not-fired.
    """

    def __init__(
        self,
        rng: SeededRandom,
        rules: Sequence[FaultRule],
        *,
        allow_destructive: bool = False,
    ) -> None:
        self._rng = rng
        self._rules: tuple[FaultRule, ...] = tuple(rules)
        self.allow_destructive = allow_destructive
        self._destructive_locked = False
        self._fires: list[int] = [0] * len(self._rules)
        self._history: list[FaultDecision] = []

    @classmethod
    def parse(
        cls,
        dsl: str,
        rng: SeededRandom,
        *,
        allow_destructive: bool = False,
    ) -> FaultSchedule:
        """Build a schedule from a fail-rs DSL string, validating eagerly.

        Grammar: ``->``-separated segments, each
        ``[<prob>%][<count>*]<action>[(<args>)]``. Example:
        ``"20%3*delay(250)->10%drop"`` = up to 3 times, 20% chance, delay 250ms;
        otherwise 10% chance drop.

        Args:
            dsl (str): The fault DSL string.
            rng (SeededRandom): The seeded RNG providing derived draws.
            allow_destructive (bool): Gate for state-mutating faults.

        Returns:
            FaultSchedule: The validated schedule.
        """
        text = dsl.strip()
        if text == "":
            return cls(rng, (), allow_destructive=allow_destructive)
        segments = [s for s in text.split("->")]
        rules = [_parse_segment(s) for s in segments]
        return cls(rng, rules, allow_destructive=allow_destructive)

    def disable_destructive(self) -> None:
        """Permanently forbid destructive (state-mutating) faults on this schedule.

        Called by ChaosResource when the wrapped backend is remote/externally-
        owned: a ChaosResource must never mutate a real remote, so dup / partial
        / lost_ack are gated off at the decision chokepoint. After this call,
        destructive rules are recorded as not-fired (the replay log stays honest)
        and the gate cannot be re-enabled.

        Args:
            None

        Returns:
            None
        """
        self.allow_destructive = False
        self._destructive_locked = True

    def _rule_enabled(self, rule: FaultRule) -> bool:
        """Return whether a rule is permitted to fire under the safety gate.

        Args:
            rule (FaultRule): The candidate rule.

        Returns:
            bool: False when a destructive action is not permitted.
        """
        if rule.action in DESTRUCTIVE_ACTIONS and not self.allow_destructive:
            return False
        return True

    def decide(
        self,
        *,
        op_index: int,
        site: str,
        path_key: str,
    ) -> FaultDecision:
        """Decide whether a fault fires at one op-site and record the decision.

        Args:
            op_index (int): The monotonic op index of the op-site.
            site (str): The op-site method name (e.g. ``"write"``).
            path_key (str): The normalized path key the op targets.

        Returns:
            FaultDecision: The (recorded) decision for this op-site.
        """
        chosen: FaultDecision | None = None
        last_draw = 0.0
        for idx, rule in enumerate(self._rules):
            if not rule.scope.matches(
                site=site, path_key=path_key, op_index=op_index
            ):
                continue
            draw = self._rng.derive_unit(
                op_index=op_index, site=site, key=f"{path_key}#rule{idx}"
            )
            last_draw = draw
            if draw >= rule.prob:
                continue
            if not self._rule_enabled(rule):
                continue
            if rule.max_fires is not None and self._fires[idx] >= rule.max_fires:
                continue
            self._fires[idx] += 1
            chosen = FaultDecision(
                op_index=op_index,
                site=site,
                path_key=path_key,
                draw=draw,
                fired=True,
                action=rule.action,
            )
            break
        if chosen is None:
            chosen = FaultDecision(
                op_index=op_index,
                site=site,
                path_key=path_key,
                draw=last_draw,
                fired=False,
                action=FaultAction.OFF,
            )
        self._history.append(chosen)
        return chosen

    def rule_for(self, decision: FaultDecision) -> FaultRule | None:
        """Return the first declared rule whose action matches a fired decision.

        Args:
            decision (FaultDecision): A decision returned by ``decide``.

        Returns:
            FaultRule | None: The matching rule, or None when not fired.
        """
        if not decision.fired:
            return None
        for rule in self._rules:
            if rule.action is decision.action and rule.scope.matches(
                site=decision.site,
                path_key=decision.path_key,
                op_index=decision.op_index,
            ):
                return rule
        return None

    def history(self) -> list[FaultDecision]:
        """Return the full ordered decision log (fired and not-fired).

        Returns:
            list[FaultDecision]: A copy of the recorded decisions.
        """
        return list(self._history)

    def fork_substream(self, label: str) -> FaultSchedule:
        """Return a fresh schedule on a deterministic child RNG sub-stream.

        Args:
            label (str): Deterministic label seeding the child sub-stream.

        Returns:
            FaultSchedule: A new schedule with the same rules and a forked RNG.
        """
        child_rng = self._rng.fork_child(label)
        child = FaultSchedule(
            child_rng, self._rules, allow_destructive=self.allow_destructive
        )
        if self._destructive_locked:
            child.disable_destructive()
        return child


def _path_key(path: PathSpecLike) -> str:
    """Normalize an op path argument into a stable string key.

    Accepts either a raw string or a mirage PathSpec-like object (which exposes
    a ``key`` or ``original`` attribute) without importing mirage.

    Args:
        path (PathSpecLike): The path argument passed to an op.

    Returns:
        str: A normalized path key (leading-slash form).
    """
    key = getattr(path, "key", None)
    if key is None:
        original = getattr(path, "original", None)
        key = original if original is not None else str(path)
    text = str(key)
    return "/" + text.strip("/")


def _drift_fingerprint(value: str | None, draw: float) -> str:
    """Produce a deterministically mutated fingerprint for version drift.

    Args:
        value (str | None): The fingerprint observed from the inner backend.
        draw (float): The decision draw, used to make the mutation deterministic.

    Returns:
        str: A fingerprint string distinct from ``value``.
    """
    salt = format(int(draw * (1 << 32)) & 0xFFFFFFFF, "08x")
    base = value if value is not None else "none"
    return f"drift:{salt}:{base}"


class ChaosResource:
    """A deterministic fault-injecting wrapper around an inner mirage resource.

    The wrapper forwards every op to ``inner`` but first consults the
    FaultSchedule for the current op-site. It exposes the same async op surface
    as a mirage resource; the actual subclassing of ``BaseResource`` (so mirage
    dispatch routes through these methods) is performed in adapters.py — this
    class stays mirage-free.

    Remote safety: if the inner resource reports ``is_remote`` True, destructive
    faults (dup / partial / lost_ack) are disabled on the schedule at
    construction so a ChaosResource never mutates a real remote/externally-owned
    backend. Non-destructive faults (delay / drop / drift) still apply.

    Args:
        inner (ResourceLike): The wrapped backend resource.
        schedule (FaultSchedule): The fault schedule driving decisions.
        clock (VirtualClock): The logical clock used by the ``delay`` action.
    """

    def __init__(
        self,
        inner: ResourceLike,
        schedule: FaultSchedule,
        clock: VirtualClock,
    ) -> None:
        self._inner = inner
        self._schedule = schedule
        self._clock = clock
        self._op_index = 0
        self._fork_count = 0
        self.name = getattr(inner, "name", "chaos")
        self.is_remote = bool(getattr(inner, "is_remote", False))
        if self.is_remote:
            self._schedule.disable_destructive()

    @property
    def inner(self) -> ResourceLike:
        """The wrapped inner resource.

        Returns:
            ResourceLike: The backend this wrapper delegates to.
        """
        return self._inner

    @property
    def schedule(self) -> FaultSchedule:
        """The fault schedule driving this wrapper's decisions.

        Returns:
            FaultSchedule: The active schedule (its history is replayable).
        """
        return self._schedule

    def _next_decision(self, site: str, path: PathSpecLike) -> FaultDecision:
        """Mint the next op-index and ask the schedule for a decision.

        The op-index counter is incremented exactly once per op-site entry. This
        is atomic under single-threaded asyncio (no await between read and write
        of ``self._op_index``).

        Args:
            site (str): The op-site method name.
            path (PathSpecLike): The path argument of the op.

        Returns:
            FaultDecision: The decision for this op-site.
        """
        op_index = self._op_index
        self._op_index += 1
        return self._schedule.decide(
            op_index=op_index, site=site, path_key=_path_key(path)
        )

    def fork(self) -> ChaosResource:
        """Fork the wrapper, forking the inner resource and the RNG sub-stream.

        The child's fault sub-stream label folds in a monotonic per-parent fork
        counter (``fork:<name>#<n>``) so two sibling forks of the SAME parent
        get DISTINCT sub-streams and therefore independent fault decisions —
        without it, both children would label as ``fork:<name>`` and replay
        byte-identical faults. The counter is a pure function of how many times
        this parent has been forked (deterministic under the serial driving the
        state machine uses); no wall-clock or unseeded randomness is consulted,
        so the whole fork DAG still replays from the seed alone.

        Args:
            None

        Returns:
            ChaosResource: A child wrapper over ``inner.fork()`` with a forked,
            deterministic fault sub-stream sharing the same clock.
        """
        fork_ordinal = self._fork_count
        self._fork_count += 1
        child_inner = self._inner.fork()
        child_schedule = self._schedule.fork_substream(
            f"fork:{self.name}#{fork_ordinal}"
        )
        return ChaosResource(child_inner, child_schedule, self._clock)

    async def fingerprint(self, path: PathSpecLike) -> str | None:
        """Return the inner fingerprint, optionally mutated by version drift.

        Version drift only applies when the inner fingerprint is meaningful
        (not None); a None fingerprint is forwarded unchanged so drift cannot
        manufacture freshness information that the backend does not provide.

        Args:
            path (PathSpecLike): The path to fingerprint.

        Returns:
            str | None: The (possibly drifted) fingerprint.
        """
        decision = self._next_decision("fingerprint", path)
        value = await self._inner.fingerprint(_path_key(path))
        if decision.fired and decision.action is FaultAction.VERSION_DRIFT:
            if value is not None:
                return _drift_fingerprint(value, decision.draw)
        return value

    async def read_bytes(self, path: PathSpecLike) -> bytes:
        """Read file bytes, applying read-side faults (delay / drop / dup).

        Args:
            path (PathSpecLike): The file path to read.

        Returns:
            bytes: The file contents.
        """
        decision = self._next_decision("read_bytes", path)
        if decision.fired and decision.action is FaultAction.DELAY:
            await self._delay(decision)
            return await self._inner.read_bytes(path)
        if decision.fired and decision.action is FaultAction.DROP:
            raise SimulatedFault(
                "simulated read_bytes drop",
                site="read_bytes",
                path_key=decision.path_key,
            )
        if decision.fired and decision.action is FaultAction.DUPLICATE:
            await self._inner.read_bytes(path)
            return await self._inner.read_bytes(path)
        return await self._inner.read_bytes(path)

    async def write(self, path: PathSpecLike, data: bytes) -> None:
        """Write file bytes, applying write-side faults.

        Action semantics:
            drop      raise before writing (effect never lands).
            delay     logical delay then write.
            dup       write twice.
            partial   write the first k/n byte-chunks then raise (torn write).
            lost_ack  write the full payload then raise SimulatedLostAck.

        Args:
            path (PathSpecLike): The file path to write.
            data (bytes): The payload bytes.

        Returns:
            None
        """
        decision = self._next_decision("write", path)
        if not decision.fired:
            await self._inner.write(path, data)
            return
        action = decision.action
        if action is FaultAction.DROP:
            raise SimulatedFault(
                "simulated write drop",
                site="write",
                path_key=decision.path_key,
            )
        if action is FaultAction.DELAY:
            await self._delay(decision)
            await self._inner.write(path, data)
            return
        if action is FaultAction.DUPLICATE:
            await self._inner.write(path, data)
            await self._inner.write(path, data)
            return
        if action is FaultAction.PARTIAL:
            await self._partial_write(path, data, decision)
            return
        if action is FaultAction.LOST_ACK:
            await self._inner.write(path, data)
            raise SimulatedLostAck(
                "simulated write lost ack (effect landed)",
                site="write",
                path_key=decision.path_key,
            )
        await self._inner.write(path, data)

    async def _partial_write(
        self,
        path: PathSpecLike,
        data: bytes,
        decision: FaultDecision,
    ) -> None:
        """Commit the first k of n chunks of a write, then raise a torn-write.

        The payload is split into n contiguous chunks; the first k are committed
        to the inner backend as the new file contents, then a SimulatedFault is
        raised so the caller observes a torn write.

        Args:
            path (PathSpecLike): The file path to write.
            data (bytes): The full payload bytes.
            decision (FaultDecision): The fired partial decision.

        Returns:
            None
        """
        rule = self._schedule.rule_for(decision)
        params: Mapping[str, Any] = rule.params if rule is not None else {}
        n = int(params.get("n", 2))
        k = int(params.get("k", 1))
        if n <= 0:
            n = 1
        if k < 0:
            k = 0
        if k >= n:
            k = n - 1
        total = len(data)
        chunk = (total + n - 1) // n if n > 0 else total
        prefix = data[: chunk * k]
        await self._inner.write(path, prefix)
        raise SimulatedFault(
            f"simulated partial write (committed {len(prefix)}/{total} bytes)",
            site="write",
            path_key=decision.path_key,
        )

    async def append(self, path: PathSpecLike, data: bytes) -> None:
        """Append bytes to a file, applying append-side faults.

        Args:
            path (PathSpecLike): The file path to append to.
            data (bytes): The bytes to append.

        Returns:
            None
        """
        decision = self._next_decision("append", path)
        if not decision.fired:
            await self._inner.append(path, data)
            return
        action = decision.action
        if action is FaultAction.DROP:
            raise SimulatedFault(
                "simulated append drop",
                site="append",
                path_key=decision.path_key,
            )
        if action is FaultAction.DELAY:
            await self._delay(decision)
            await self._inner.append(path, data)
            return
        if action is FaultAction.DUPLICATE:
            await self._inner.append(path, data)
            await self._inner.append(path, data)
            return
        if action is FaultAction.LOST_ACK:
            await self._inner.append(path, data)
            raise SimulatedLostAck(
                "simulated append lost ack (effect landed)",
                site="append",
                path_key=decision.path_key,
            )
        if action is FaultAction.PARTIAL:
            await self._partial_write(path, data, decision)
            return
        await self._inner.append(path, data)

    async def readdir(self, path: PathSpecLike, index: Any) -> list[str]:
        """List a directory, applying read-side faults (delay / drop / dup).

        Args:
            path (PathSpecLike): The directory path to list.
            index (Any): The mirage index argument, forwarded unchanged.

        Returns:
            list[str]: The directory entries.
        """
        decision = self._next_decision("readdir", path)
        if decision.fired and decision.action is FaultAction.DELAY:
            await self._delay(decision)
            return await self._inner.readdir(path, index)
        if decision.fired and decision.action is FaultAction.DROP:
            raise SimulatedFault(
                "simulated readdir drop",
                site="readdir",
                path_key=decision.path_key,
            )
        if decision.fired and decision.action is FaultAction.DUPLICATE:
            await self._inner.readdir(path, index)
            return await self._inner.readdir(path, index)
        return await self._inner.readdir(path, index)

    async def stat(self, path: PathSpecLike, index: Any = None) -> Any:
        """Stat a path, applying read-side faults (delay / drop / dup).

        Args:
            path (PathSpecLike): The path to stat.
            index (Any): The mirage index argument, forwarded unchanged.

        Returns:
            Any: The backend stat result.
        """
        decision = self._next_decision("stat", path)
        if decision.fired and decision.action is FaultAction.DELAY:
            await self._delay(decision)
            return await self._inner.stat(path, index)
        if decision.fired and decision.action is FaultAction.DROP:
            raise SimulatedFault(
                "simulated stat drop",
                site="stat",
                path_key=decision.path_key,
            )
        if decision.fired and decision.action is FaultAction.DUPLICATE:
            await self._inner.stat(path, index)
            return await self._inner.stat(path, index)
        return await self._inner.stat(path, index)

    async def unlink(self, path: PathSpecLike) -> None:
        """Remove a file, applying unlink-side faults.

        Args:
            path (PathSpecLike): The file path to remove.

        Returns:
            None
        """
        decision = self._next_decision("unlink", path)
        if not decision.fired:
            await self._inner.unlink(path)
            return
        action = decision.action
        if action is FaultAction.DROP:
            raise SimulatedFault(
                "simulated unlink drop",
                site="unlink",
                path_key=decision.path_key,
            )
        if action is FaultAction.DELAY:
            await self._delay(decision)
            await self._inner.unlink(path)
            return
        if action is FaultAction.DUPLICATE:
            await self._inner.unlink(path)
            await self._duplicate_unlink(path)
            return
        if action is FaultAction.LOST_ACK:
            await self._inner.unlink(path)
            raise SimulatedLostAck(
                "simulated unlink lost ack (effect landed)",
                site="unlink",
                path_key=decision.path_key,
            )
        await self._inner.unlink(path)

    async def _duplicate_unlink(self, path: PathSpecLike) -> None:
        """Re-issue an unlink, tolerating a missing-file error on the retry.

        An at-least-once duplicate of a delete may legitimately find the target
        already gone; that specific FileNotFoundError is the expected, benign
        outcome of the duplication and is intentionally absorbed. Any other error
        propagates.

        Args:
            path (PathSpecLike): The file path to remove again.

        Returns:
            None
        """
        try:
            await self._inner.unlink(path)
        except FileNotFoundError:
            return

    async def read_stream(
        self,
        path: PathSpecLike,
        index: Any = None,
    ) -> AsyncIterator[bytes]:
        """Stream file bytes, applying read-side faults.

        For ``drop`` the stream raises before any chunk is yielded. For ``delay``
        a logical delay precedes the first chunk. The inner async generator is
        always closed in a finally block so an interrupted stream never leaks an
        open generator.

        Args:
            path (PathSpecLike): The file path to stream.
            index (Any): The mirage index argument, forwarded unchanged.

        Yields:
            bytes: Successive chunks of file content.
        """
        decision = self._next_decision("read_stream", path)
        if decision.fired and decision.action is FaultAction.DROP:
            raise SimulatedFault(
                "simulated read_stream drop",
                site="read_stream",
                path_key=decision.path_key,
            )
        if decision.fired and decision.action is FaultAction.DELAY:
            await self._delay(decision)
        inner_iter = self._inner.read_stream(path, index)
        try:
            async for chunk in inner_iter:
                yield chunk
        finally:
            aclose = getattr(inner_iter, "aclose", None)
            if aclose is not None:
                await aclose()

    async def _delay(self, decision: FaultDecision) -> None:
        """Advance the logical clock by the rule's configured delay.

        Uses ``clock.sim_sleep`` (logical time only); never a real sleep. If the
        fired rule cannot be located the delay is treated as zero so the op still
        yields control once via the clock.

        Args:
            decision (FaultDecision): The fired delay decision.

        Returns:
            None
        """
        rule = self._schedule.rule_for(decision)
        seconds = 0.0
        if rule is not None:
            seconds = float(rule.params.get("delay", 0.0))
        await self._clock.sim_sleep(seconds)
