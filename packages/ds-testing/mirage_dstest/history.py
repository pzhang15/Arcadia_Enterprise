"""Operation history recording and scoped consistency checking.

This module records operation histories in the Porcupine/Jepsen two-row-per-op
shape (an ``invoke`` row followed by a ``complete`` row carrying an
:class:`OpStatus`) and provides two cheap, scoped consistency checkers over a
recorded history.

Time source
-----------
Every timestamp comes ONLY from the injected ``VirtualClock.now()``, captured as
close to the await boundary as possible so logical time is monotonic and
single-sourced. There is no wall-clock and no unseeded randomness here.

Real-time interval convention
-----------------------------
For an operation, ``[invoke_t, complete_t]`` is a CLOSED real-time interval
(Porcupine convention): operation ``a`` happens-before operation ``b`` iff
``a.complete_t <= b.invoke_t``. The bound is ``<=`` (not ``<``); operations whose
intervals touch at a single instant are treated as concurrent, not ordered.
Treating this as a half-open interval flips real-time edges and changes results.

Operation value conventions (what the checkers parse)
-----------------------------------------------------
The checkers read ``HistoryEntry.f`` (the operation name) and
``HistoryEntry.value`` (its operand or result). Two workload shapes are
recognized:

Unique register (``check_unique_register``)
    - write: ``f == "write"`` (also ``"w"``/``"append"`` accepted), ``value``
      is either ``(key, written_value)`` or a bare ``written_value`` (single
      global register under the sentinel key).
    - read: ``f == "read"`` (also ``"r"`` accepted), ``value`` is either
      ``(key, observed_value)`` or a bare ``observed_value``.
    Precondition: every write value is distinct per key (that is the
    "unique register" assumption that makes the fast linearizability gate
    sound). A non-distinct write is itself reported as ``dup-write``.

List append (``check_list_append``)
    - append: ``f == "append"`` (also ``"w"`` accepted), ``value`` is
      ``(key, element)`` or a bare ``element``.
    - read: ``f == "read"`` (also ``"r"`` accepted), ``value`` is
      ``(key, list_of_elements)`` or a bare ``list_of_elements``.

Soundness, not completeness
---------------------------
Both checkers are SOUND but NOT COMPLETE: a returned anomaly is a genuine
witnessed violation, but an empty result means "no anomaly was witnessed by
these checks" — it is NOT a proof of linearizability or serializability.
A full WGL/Porcupine search (bounded by a timeout and reporting Unknown rather
than Pass) is intentionally out of scope here; only the two cheap checkers ship.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, Sequence

import networkx as nx

if TYPE_CHECKING:
    from mirage_dstest.clock import VirtualClock


_SINGLE_KEY = "__single__"
_WRITE_OPS = frozenset({"write", "w", "append"})
_READ_OPS = frozenset({"read", "r"})
_APPEND_OPS = frozenset({"append", "w"})


class OpStatus(str, Enum):
    OK = "ok"
    FAIL = "fail"
    INFO = "info"


@dataclass(frozen=True)
class HistoryEntry:
    process: int
    kind: Literal["invoke", "complete"]
    f: str
    value: Any
    t: float
    status: OpStatus | None = None


@dataclass
class _RecordHandle:
    status: OpStatus = OpStatus.OK
    value: Any = None

    def fail(self, *, value: Any = None) -> None:
        """Mark the in-flight operation as a definite FAIL (effect did not apply).

        Args:
            value (Any): Optional value to record on the completion row.
        """
        self.status = OpStatus.FAIL
        if value is not None:
            self.value = value

    def set_value(self, value: Any) -> None:
        """Set the value recorded on the completion row for an OK operation.

        Args:
            value (Any): The operation's result value (e.g. bytes read).
        """
        self.value = value


@dataclass(frozen=True)
class Anomaly:
    kind: str
    cycle: list[int]
    detail: str


class HistoryRecorder:
    def __init__(self, clock: VirtualClock) -> None:
        """Create a recorder bound to a single monotonic logical clock.

        Args:
            clock (VirtualClock): The sole time source; ``clock.now()`` stamps
                every invoke and complete row.
        """
        self._clock = clock
        self._entries: list[HistoryEntry] = []
        self._open: dict[int, HistoryEntry] = {}

    def invoke(self, *, process: int, f: str, value: Any) -> int:
        """Record an invoke row and return an opaque op handle.

        The timestamp is captured immediately from ``clock.now()``.

        Args:
            process (int): Logical process / actor id issuing the operation.
            f (str): Operation name (e.g. ``"write"``, ``"read"``, ``"append"``).
            value (Any): The operation's operand (input) at invocation time.

        Returns:
            int: A handle (the invoke row's index) to pass to ``complete``.
        """
        entry = HistoryEntry(
            process=process,
            kind="invoke",
            f=f,
            value=value,
            t=self._clock.now(),
            status=None,
        )
        handle = len(self._entries)
        self._entries.append(entry)
        self._open[handle] = entry
        return handle

    def complete(self, handle: int, *, status: OpStatus, value: Any = None) -> None:
        """Record the matching complete row for a previously invoked op.

        The timestamp is captured immediately from ``clock.now()``; together with
        the invoke timestamp it forms the closed ``[invoke_t, complete_t]``
        real-time interval.

        Args:
            handle (int): The handle returned by ``invoke``.
            status (OpStatus): Outcome — OK, FAIL (did not apply), or INFO
                (indeterminate / possibly applied).
            value (Any): The operation's result value (defaults to None).

        Raises:
            KeyError: If ``handle`` is unknown or already completed.
        """
        if handle not in self._open:
            raise KeyError(f"unknown or already-completed op handle: {handle}")
        invoke_entry = self._open.pop(handle)
        self._entries.append(
            HistoryEntry(
                process=invoke_entry.process,
                kind="complete",
                f=invoke_entry.f,
                value=value,
                t=self._clock.now(),
                status=status,
            )
        )

    @contextlib.asynccontextmanager
    async def record(self, *, process: int, f: str, value: Any):
        """Auto-record an operation's invoke/complete pair around a block.

        Yields a handle whose ``.fail(...)`` marks the operation as a definite
        FAIL and ``.set_value(...)`` records the result on the OK completion row.
        On normal exit the operation completes OK (or FAIL if the caller marked
        it). If the body raises, the operation completes as INFO
        (indeterminate / possibly applied) unless the caller explicitly marked
        FAIL, and the exception is RE-RAISED (never swallowed).

        Args:
            process (int): Logical process / actor id issuing the operation.
            f (str): Operation name.
            value (Any): The operation's operand at invocation time.

        Yields:
            _RecordHandle: Mutable handle exposing ``fail`` and ``set_value``.
        """
        handle = self.invoke(process=process, f=f, value=value)
        record_handle = _RecordHandle()
        try:
            yield record_handle
        except BaseException:
            final_status = (
                OpStatus.FAIL
                if record_handle.status is OpStatus.FAIL
                else OpStatus.INFO
            )
            self.complete(handle, status=final_status, value=record_handle.value)
            raise
        else:
            self.complete(
                handle, status=record_handle.status, value=record_handle.value
            )

    def entries(self) -> list[HistoryEntry]:
        """Return a shallow copy of all recorded rows in record order.

        Returns:
            list[HistoryEntry]: Invoke/complete rows, oldest first.
        """
        return list(self._entries)

    def to_edn_dicts(self) -> list[dict]:
        """Return Jepsen-shaped maps for optional offline Knossos/Elle cross-check.

        Each row maps to ``{:process, :type, :f, :value, :time}`` where ``:type``
        is ``:invoke`` for invoke rows and the completion ``OpStatus`` value
        (``:ok``/``:fail``/``:info``) for complete rows.

        Returns:
            list[dict]: One dict per recorded row, in record order.
        """
        out: list[dict] = []
        for entry in self._entries:
            if entry.kind == "invoke":
                row_type = "invoke"
            elif entry.status is not None:
                row_type = entry.status.value
            else:
                row_type = "info"
            out.append(
                {
                    "process": entry.process,
                    "type": row_type,
                    "f": entry.f,
                    "value": entry.value,
                    "time": entry.t,
                }
            )
        return out


@dataclass
class _Op:
    invoke_index: int
    process: int
    f: str
    invoke_value: Any
    complete_value: Any
    invoke_t: float
    complete_t: float
    status: OpStatus


def _pair_ops(history: Sequence[HistoryEntry]) -> list[_Op]:
    """Pair invoke rows with their completions into operation records.

    An invoke without a completion is treated as INFO with ``complete_t`` equal
    to ``+inf`` (it overlaps everything after it), so it can never be ordered
    real-time-before another op. Operations are returned in invoke order.

    Args:
        history (Sequence[HistoryEntry]): The recorded rows.

    Returns:
        list[_Op]: One record per invoked operation.
    """
    open_ops: dict[int, _Op] = {}
    order: list[int] = []
    pending: dict[int, list[int]] = {}
    next_invoke: dict[int, int] = {}
    for idx, entry in enumerate(history):
        if entry.kind == "invoke":
            op = _Op(
                invoke_index=idx,
                process=entry.process,
                f=entry.f,
                invoke_value=entry.value,
                complete_value=None,
                invoke_t=entry.t,
                complete_t=float("inf"),
                status=OpStatus.INFO,
            )
            open_ops[idx] = op
            order.append(idx)
            pending.setdefault(entry.process, []).append(idx)
            next_invoke[entry.process] = idx
        else:
            queue = pending.get(entry.process)
            if not queue:
                continue
            target = queue.pop(0)
            op = open_ops[target]
            op.complete_value = entry.value
            op.complete_t = entry.t
            op.status = entry.status if entry.status is not None else OpStatus.INFO
    return [open_ops[i] for i in order]


def _split_key_value(value: Any) -> tuple[Any, Any]:
    """Split an operation value into ``(key, payload)``.

    A 2-tuple/2-list is treated as ``(key, payload)``; anything else is a bare
    payload under the single-register sentinel key.

    Args:
        value (Any): The operation's recorded value.

    Returns:
        tuple[Any, Any]: ``(key, payload)``.
    """
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return value[0], value[1]
    return _SINGLE_KEY, value


class ScopedConsistencyChecker:
    def __init__(self, history: Sequence[HistoryEntry]) -> None:
        """Build a checker over a recorded history.

        Args:
            history (Sequence[HistoryEntry]): Invoke/complete rows from a
                :class:`HistoryRecorder`.
        """
        self._ops = _pair_ops(history)

    def check_unique_register(self) -> list[Anomaly]:
        """Fast unique-register linearizability gate (Gibbons-Korach style).

        Assumes each write to a key carries a distinct value (the unique-register
        precondition), giving an ``O(n log n)`` check instead of a full search.
        Witnesses three sound anomalies per key:

        - ``dup-write``: two writes carry the same value (the precondition is
          violated, so the fast gate cannot run soundly for that key).
        - ``non-unique-register`` (torn): a read returns a value that was never
          written to that key.
        - ``non-unique-register`` (stale): a read of value ``v`` completes after
          some write ``w != v`` whose interval is entirely real-time-before the
          read, while ``v``'s own write is real-time-before ``w`` — i.e. ``v`` is
          read strictly after it was provably overwritten, which no
          linearization permits.

        This is SOUND but NOT COMPLETE: an empty result is "no anomaly
        witnessed", not a proof of linearizability.

        Returns:
            list[Anomaly]: Witnessed anomalies (possibly empty).
        """
        writes_by_key: dict[Any, dict[Any, list[_Op]]] = {}
        reads_by_key: dict[Any, list[_Op]] = {}
        for op in self._ops:
            if op.status is OpStatus.FAIL:
                continue
            if op.f in _WRITE_OPS:
                key, payload = _split_key_value(op.invoke_value)
                writes_by_key.setdefault(key, {}).setdefault(payload, []).append(op)
            elif op.f in _READ_OPS:
                key, payload = _split_key_value(op.complete_value)
                reads_by_key.setdefault(key, []).append((op, payload))  # type: ignore[arg-type]

        anomalies: list[Anomaly] = []
        for key, by_value in writes_by_key.items():
            for payload, ops in by_value.items():
                if len(ops) > 1:
                    cycle = sorted(op.invoke_index for op in ops)
                    anomalies.append(
                        Anomaly(
                            kind="dup-write",
                            cycle=cycle,
                            detail=(
                                f"key={key!r} value={payload!r} written by "
                                f"{len(ops)} ops {cycle} (unique-register "
                                "precondition violated)"
                            ),
                        )
                    )
        anomalies.extend(self._check_register_reads(writes_by_key, reads_by_key))
        return anomalies

    def _check_register_reads(
        self,
        writes_by_key: dict[Any, dict[Any, list[_Op]]],
        reads_by_key: dict[Any, list[Any]],
    ) -> list[Anomaly]:
        """Witness torn and stale reads against unique writers.

        Args:
            writes_by_key (dict): ``key -> value -> [write ops]``.
            reads_by_key (dict): ``key -> [(read op, observed value)]``.

        Returns:
            list[Anomaly]: ``non-unique-register`` anomalies (possibly empty).
        """
        anomalies: list[Anomaly] = []
        for key, reads in reads_by_key.items():
            by_value = writes_by_key.get(key, {})
            for read_op, observed in reads:
                if observed is None:
                    continue
                writers = by_value.get(observed)
                if not writers:
                    anomalies.append(
                        Anomaly(
                            kind="non-unique-register",
                            cycle=[read_op.invoke_index],
                            detail=(
                                f"key={key!r} read value={observed!r} that was "
                                "never written (torn read)"
                            ),
                        )
                    )
                    continue
                if len(writers) > 1:
                    continue
                writer = writers[0]
                stale = self._stale_read_anomaly(key, observed, read_op, writer, by_value)
                if stale is not None:
                    anomalies.append(stale)
        return anomalies

    def _stale_read_anomaly(
        self,
        key: Any,
        observed: Any,
        read_op: _Op,
        writer: _Op,
        by_value: dict[Any, list[_Op]],
    ) -> Anomaly | None:
        """Witness a read of a value that was provably overwritten before it.

        Args:
            key (Any): The register key.
            observed (Any): The value the read returned.
            read_op (_Op): The read operation.
            writer (_Op): The unique writer of ``observed``.
            by_value (dict): ``value -> [write ops]`` for this key.

        Returns:
            Anomaly | None: A ``non-unique-register`` anomaly if witnessed.
        """
        for other_value, other_writers in by_value.items():
            if other_value == observed or len(other_writers) != 1:
                continue
            other = other_writers[0]
            overwrites = writer.complete_t <= other.invoke_t
            read_after_overwrite = other.complete_t <= read_op.invoke_t
            if overwrites and read_after_overwrite:
                return Anomaly(
                    kind="non-unique-register",
                    cycle=sorted(
                        {writer.invoke_index, other.invoke_index, read_op.invoke_index}
                    ),
                    detail=(
                        f"key={key!r} read value={observed!r} (written by op "
                        f"{writer.invoke_index}) after it was overwritten by "
                        f"value={other_value!r} (op {other.invoke_index}); read "
                        f"op {read_op.invoke_index} cannot observe a stale value "
                        "under a unique register"
                    ),
                )
        return None

    def check_list_append(self, *, partition_by_key: bool = True) -> list[Anomaly]:
        """Elle-style list-append cycle detection.

        Builds a dependency graph over append/read operations and reports cycles
        found by ``networkx.simple_cycles``. Edge kinds:

        - program-order (``po``): consecutive ops by the same process.
        - write-read (``wr``): a read observing element ``x`` depends on the
          append of ``x``.
        - write-write (``ww``): append order inferred from the order elements
          appear in observed list reads.
        - read-write (``rw``): a read that does NOT observe element ``x`` must
          precede ``x``'s append (anti-dependency).

        Cycle classification (best-effort, by the edge kinds in the cycle):
        a cycle with no ``rw`` and at least one ``wr`` is ``G1c``; a cycle with
        exactly one ``rw`` is ``G-single``; a cycle of only ``ww`` (and ``po``)
        is ``G0``.

        This is SOUND but NOT COMPLETE: an empty result is "no anomaly
        witnessed", not a proof of serializability.

        Args:
            partition_by_key (bool): If True, build per-key dependency edges
                (the default; ww/wr/rw are inherently per-key). Program-order
                edges always span keys.

        Returns:
            list[Anomaly]: Witnessed anomalies, one per distinct simple cycle.
        """
        graph: nx.DiGraph = nx.DiGraph()
        for op in self._ops:
            if op.status is OpStatus.FAIL:
                continue
            graph.add_node(op.invoke_index)
        self._add_program_order_edges(graph)
        appends, reads = self._collect_appends_reads()
        if partition_by_key:
            keys = set(appends) | set(reads)
        else:
            keys = {_SINGLE_KEY}
        for key in keys:
            self._add_append_read_edges(
                graph,
                appends.get(key, {}),
                reads.get(key, []),
            )
        return self._cycles_to_anomalies(graph)

    def _add_program_order_edges(self, graph: nx.DiGraph) -> None:
        """Add per-process program-order edges between consecutive ops.

        Args:
            graph (nx.DiGraph): The dependency graph being built.
        """
        last_by_process: dict[int, int] = {}
        for op in self._ops:
            if op.status is OpStatus.FAIL:
                continue
            prev = last_by_process.get(op.process)
            if prev is not None:
                self._add_edge(graph, prev, op.invoke_index, "po")
            last_by_process[op.process] = op.invoke_index

    def _collect_appends_reads(
        self,
    ) -> tuple[dict[Any, dict[Any, _Op]], dict[Any, list[Any]]]:
        """Index append ops by ``(key, element)`` and read ops by key.

        Returns:
            tuple: ``(appends, reads)`` where ``appends`` is
                ``key -> element -> append op`` and ``reads`` is
                ``key -> [(read op, observed list)]``.
        """
        appends: dict[Any, dict[Any, _Op]] = {}
        reads: dict[Any, list[Any]] = {}
        for op in self._ops:
            if op.status is OpStatus.FAIL:
                continue
            if op.f in _APPEND_OPS:
                key, element = _split_key_value(op.invoke_value)
                appends.setdefault(key, {})[element] = op
            elif op.f in _READ_OPS:
                key, observed = _split_key_value(op.complete_value)
                if isinstance(observed, (list, tuple)):
                    reads.setdefault(key, []).append((op, list(observed)))  # type: ignore[arg-type]
        return appends, reads

    def _add_append_read_edges(
        self,
        graph: nx.DiGraph,
        appends: dict[Any, _Op],
        reads: list[Any],
    ) -> None:
        """Add ww/wr/rw edges for one key.

        Args:
            graph (nx.DiGraph): The dependency graph being built.
            appends (dict): ``element -> append op`` for this key.
            reads (list): ``[(read op, observed list)]`` for this key.
        """
        for read_op, observed in reads:
            seen: set[Any] = set()
            prev_index: int | None = None
            for element in observed:
                append_op = appends.get(element)
                seen.add(element)
                if append_op is None:
                    continue
                self._add_edge(graph, append_op.invoke_index, read_op.invoke_index, "wr")
                if prev_index is not None and prev_index != append_op.invoke_index:
                    self._add_edge(graph, prev_index, append_op.invoke_index, "ww")
                prev_index = append_op.invoke_index
            for element, append_op in appends.items():
                if element not in seen:
                    self._add_edge(
                        graph, read_op.invoke_index, append_op.invoke_index, "rw"
                    )

    def _add_edge(self, graph: nx.DiGraph, src: int, dst: int, kind: str) -> None:
        """Add a typed edge, accumulating kinds when an edge already exists.

        Args:
            graph (nx.DiGraph): The dependency graph being built.
            src (int): Source op index.
            dst (int): Destination op index.
            kind (str): Edge kind (``po``/``wr``/``ww``/``rw``).
        """
        if src == dst:
            return
        if graph.has_edge(src, dst):
            graph[src][dst]["kinds"].add(kind)
        else:
            graph.add_edge(src, dst, kinds={kind})

    def _cycles_to_anomalies(self, graph: nx.DiGraph) -> list[Anomaly]:
        """Classify each simple cycle in the graph into an anomaly.

        Args:
            graph (nx.DiGraph): The completed dependency graph.

        Returns:
            list[Anomaly]: One anomaly per distinct simple cycle.
        """
        anomalies: list[Anomaly] = []
        for cycle in nx.simple_cycles(graph):
            kinds = self._cycle_edge_kinds(graph, cycle)
            kind = self._classify_cycle(kinds)
            anomalies.append(
                Anomaly(
                    kind=kind,
                    cycle=list(cycle),
                    detail=(
                        f"dependency cycle over ops {list(cycle)} "
                        f"with edge kinds {sorted(kinds)}"
                    ),
                )
            )
        return anomalies

    def _cycle_edge_kinds(self, graph: nx.DiGraph, cycle: list[int]) -> set[str]:
        """Collect the edge kinds traversed around a cycle.

        Args:
            graph (nx.DiGraph): The dependency graph.
            cycle (list[int]): Node sequence of a simple cycle.

        Returns:
            set[str]: Union of edge kinds on the cycle's edges.
        """
        kinds: set[str] = set()
        length = len(cycle)
        for i in range(length):
            src = cycle[i]
            dst = cycle[(i + 1) % length]
            data = graph.get_edge_data(src, dst)
            if data is not None:
                kinds |= data["kinds"]
        return kinds

    def _classify_cycle(self, kinds: set[str]) -> str:
        """Map a cycle's edge kinds to an anomaly label.

        Args:
            kinds (set[str]): Edge kinds present on the cycle.

        Returns:
            str: ``'G0'`` | ``'G1c'`` | ``'G-single'``.
        """
        rw_count = 1 if "rw" in kinds else 0
        if rw_count == 0:
            if "wr" in kinds:
                return "G1c"
            return "G0"
        return "G-single"

    def check(self) -> list[Anomaly]:
        """Run the applicable cheap checkers and aggregate their anomalies.

        Runs both the unique-register gate and the list-append cycle detector;
        each is sound and only reports anomalies for the workload shape it
        recognizes, so running both is safe. An empty list means "no anomaly
        witnessed" — NOT a proof of correctness.

        Returns:
            list[Anomaly]: All witnessed anomalies (possibly empty).
        """
        anomalies: list[Anomaly] = []
        anomalies.extend(self.check_unique_register())
        anomalies.extend(self.check_list_append())
        return anomalies
