"""Backend contract-suite for the mirage_dstest harness.

This module defines ONE parametrized conformance suite that every backend
Resource (RAM / Disk / fake-S3) must pass. The assertions are written as
backend-agnostic async functions plus a factory ``Protocol``; the consumer
(a test module that owns the runtime ``mirage`` import) supplies concrete
``ResourceFactory`` implementations whose ``make()`` returns an adapted view
that satisfies both the ``ResourceLike`` surface and the ``SystemUnderTest``
read/write protocol used here.

This module imports cleanly with NO ``mirage`` installed: all ``mirage`` types
are referenced only through ``Protocol`` aliases (``ResourceLike`` from
``protocols``) and ``TYPE_CHECKING`` annotations. The only runtime
mirage-coupling module is ``adapters``, which the CONSUMER imports, not this
file.

Fork-isolation note (research pitfall): only local content-backed resources
(RAM = copy-on-write, Disk = eager copy) isolate a child's writes from its
parent. Remote / by-reference backends (S3, Slack, ...) share state, so it
would be WRONG to assert isolation for them. ``assert_fork_isolation_if_local``
therefore short-circuits via ``factory.supports_local_fork_isolation()``.

Path convention: every path is a leading-slash POSIX-style absolute path
(e.g. ``"/a/b.txt"``), matching ``ModelFS``. The consumer's adapter wraps each
str into a ``PathSpec`` at the mirage boundary.
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Protocol,
    Sequence,
    runtime_checkable,
)

from mirage_dstest.modelfs import (
    ModelFS,
    SystemUnderTest,
    assert_dir_matches,
    assert_full_state_matches,
    assert_read_matches,
)
from mirage_dstest.rng import SeededRandom

if TYPE_CHECKING:
    from mirage_dstest.protocols import ResourceLike


@runtime_checkable
class ResourceSUT(SystemUnderTest, Protocol):
    """Read/write surface the contract assertions drive a backend through.

    Extends the ``modelfs.SystemUnderTest`` read protocol (``read`` /
    ``exists`` / ``readdir``) with the minimal mutation operations the
    conformance assertions exercise. The consumer's adapter returns an object
    satisfying this protocol from ``ResourceFactory.make()`` (in mirage this
    is the resource viewed through ``adapters.workspace_sut`` plus the
    canonical writer); this module never imports mirage to obtain it.
    """

    name: str

    async def write(self, path: str, data: bytes) -> None: ...

    async def unlink(self, path: str) -> None: ...


@runtime_checkable
class ResourceFactory(Protocol):
    """Consumer-supplied factory producing a fresh backend under test.

    The concrete implementation lives in the consumer test (it imports
    ``mirage`` + ``adapters``); this module only types against the protocol so
    it stays mirage-free.

    Attributes:
        name (str): Human-readable backend label used in parametrization ids
            (e.g. ``"ram"``, ``"disk"``, ``"fake-s3"``).
    """

    name: str

    def make(self) -> "ResourceLike": ...

    def supports_local_fork_isolation(self) -> bool: ...


def _as_sut(resource: Any) -> ResourceSUT:
    """Coerce a factory-made resource view to the ``ResourceSUT`` protocol.

    The consumer's ``make()`` returns an object already adapted (via
    ``adapters``) to expose ``read`` / ``write`` / ``exists`` / ``readdir`` /
    ``unlink``. This helper validates that surface up front so a missing op
    fails with a clear ``TypeError`` at the start of an assertion rather than
    an ``AttributeError`` deep inside it. It never imports mirage.

    Args:
        resource (Any): The object returned by ``ResourceFactory.make()``.

    Returns:
        ResourceSUT: The same object, narrowed to the read/write protocol.

    Raises:
        TypeError: If ``resource`` is missing any required async operation.
    """
    required = ("read", "write", "exists", "readdir", "unlink")
    missing = [op for op in required if not callable(getattr(resource, op, None))]
    if missing:
        raise TypeError(
            "ResourceFactory.make() must return a system-under-test exposing "
            f"async ops {required}; missing {missing} on {type(resource)!r}. "
            "Wire it through adapters in the consumer."
        )
    return resource


def _ops_for_seed(rng: SeededRandom, *, steps: int) -> list[tuple[str, str, bytes]]:
    """Build a deterministic, parent-dir-safe op sequence for conformance.

    Produces a flat list of ``(op, path, data)`` triples that touch only
    root-level files (no nested directories) so it is valid against every
    backend without requiring ``mkdir``. ``op`` is one of ``"write"`` or
    ``"unlink"``. The sequence is a pure function of the RNG seed and ``steps``
    (interleaving-invariant, via ``derive_*``), making the whole conformance
    gate replayable by seed.

    Args:
        rng (SeededRandom): Seeded source; only ``derive_*`` draws are used so
            the sequence does not depend on any shared mutable generator state.
        steps (int): Number of operations to generate (``>= 0``).

    Returns:
        list[tuple[str, str, bytes]]: The op program.

    Raises:
        ValueError: If ``steps`` is negative.
    """
    if steps < 0:
        raise ValueError(f"steps must be >= 0, got {steps}")
    keyspace = 8
    program: list[tuple[str, str, bytes]] = []
    for i in range(steps):
        slot = rng.derive_int(op_index=i, site="contract.key", key="slot", bound=keyspace)
        path = f"/k{slot}.bin"
        do_unlink = rng.derive_unit(op_index=i, site="contract.op", key=path) < 0.25
        if do_unlink:
            program.append(("unlink", path, b""))
        else:
            payload_n = rng.derive_int(
                op_index=i, site="contract.len", key=path, bound=32
            )
            byte = rng.derive_int(op_index=i, site="contract.byte", key=path, bound=256)
            data = bytes([byte]) * payload_n
            program.append(("write", path, data))
    return program


async def _apply_to_model(model: ModelFS, op: str, path: str, data: bytes) -> None:
    """Apply one program op to the in-memory ``ModelFS`` twin.

    ``unlink`` of an absent key is a no-op here so the model stays in lockstep
    with a backend whose unlink-of-absent is tolerant; the chosen op program is
    write-biased so this stays a faithful mirror.

    Args:
        model (ModelFS): The reference twin to mutate.
        op (str): Either ``"write"`` or ``"unlink"``.
        path (str): Leading-slash absolute path.
        data (bytes): Payload for ``"write"`` (ignored for ``"unlink"``).

    Raises:
        ValueError: If ``op`` is not a recognized program op.
    """
    if op == "write":
        model.write(path, data)
    elif op == "unlink":
        if model.exists(path):
            model.unlink(path)
    else:
        raise ValueError(f"unknown contract op: {op!r}")


async def _apply_to_sut(sut: ResourceSUT, op: str, path: str, data: bytes) -> None:
    """Apply one program op to the backend under test.

    Mirrors ``_apply_to_model`` exactly: ``unlink`` is guarded by an
    ``exists`` probe so the backend and model agree on absent-key deletes.

    Args:
        sut (ResourceSUT): The backend under test.
        op (str): Either ``"write"`` or ``"unlink"``.
        path (str): Leading-slash absolute path.
        data (bytes): Payload for ``"write"`` (ignored for ``"unlink"``).

    Raises:
        ValueError: If ``op`` is not a recognized program op.
    """
    if op == "write":
        await sut.write(path, data)
    elif op == "unlink":
        if await sut.exists(path):
            await sut.unlink(path)
    else:
        raise ValueError(f"unknown contract op: {op!r}")


async def assert_write_read_roundtrip(factory: ResourceFactory) -> None:
    """A written byte payload reads back identical.

    Args:
        factory (ResourceFactory): Supplies a fresh backend under test.

    Raises:
        AssertionError: If the read-back bytes differ from what was written.
    """
    sut = _as_sut(factory.make())
    path = "/roundtrip.bin"
    payload = b"arcadia-ds-testing-roundtrip\x00\x01\x02"
    await sut.write(path, payload)
    got = await sut.read(path)
    if got != payload:
        raise AssertionError(
            f"[{factory.name}] write/read mismatch at {path!r}: "
            f"wrote {payload!r}, read {got!r}"
        )


async def assert_readdir_lists_children(factory: ResourceFactory) -> None:
    """``readdir`` of a directory lists exactly the names written into it.

    Compares the backend's directory listing against the ``ModelFS`` twin via
    ``assert_dir_matches`` (order-insensitive set equality on child names).

    Args:
        factory (ResourceFactory): Supplies a fresh backend under test.

    Raises:
        AssertionError: If the listed children diverge from the model.
    """
    sut = _as_sut(factory.make())
    model = ModelFS()
    names = ("alpha.txt", "beta.txt", "gamma.txt")
    for name in names:
        path = f"/{name}"
        payload = name.encode()
        await sut.write(path, payload)
        model.write(path, payload)
    await assert_dir_matches(sut, model, "/")


async def assert_unlink_then_absent(factory: ResourceFactory) -> None:
    """A key is present after write and absent after unlink.

    Args:
        factory (ResourceFactory): Supplies a fresh backend under test.

    Raises:
        AssertionError: If the key is missing after write or still present
            after unlink.
    """
    sut = _as_sut(factory.make())
    path = "/ephemeral.bin"
    await sut.write(path, b"present")
    if not await sut.exists(path):
        raise AssertionError(
            f"[{factory.name}] expected {path!r} to exist after write"
        )
    await sut.unlink(path)
    if await sut.exists(path):
        raise AssertionError(
            f"[{factory.name}] expected {path!r} to be absent after unlink"
        )


async def assert_overwrite_replaces(factory: ResourceFactory) -> None:
    """Overwriting a key replaces its contents (no append/merge).

    Args:
        factory (ResourceFactory): Supplies a fresh backend under test.

    Raises:
        AssertionError: If the second write did not fully replace the first.
    """
    sut = _as_sut(factory.make())
    model = ModelFS()
    path = "/mutable.bin"
    first = b"first-version-LONG-payload-to-detect-stale-tail"
    second = b"v2"
    await sut.write(path, first)
    model.write(path, first)
    await sut.write(path, second)
    model.write(path, second)
    await assert_read_matches(sut, model, path)


async def assert_fault_free_matches_model(
    factory: ResourceFactory, *, seed: int, steps: int = 64
) -> None:
    """Conformance gate: the in-memory twin equals the backend on a clean run.

    Drives a single seeded op program through BOTH a fresh backend (under test)
    and a ``ModelFS`` reference twin under NO fault injection, then asserts the
    full state agrees via ``assert_full_state_matches`` (every file key and the
    listing of every directory). This is the periodic in-mem-twin-vs-real
    conformance check; because the program is derived purely from ``seed`` it is
    fully replayable.

    Args:
        factory (ResourceFactory): Supplies a fresh backend under test.
        seed (int): Seed for the deterministic op program (replay key).
        steps (int): Number of operations to drive (default ``64``, ``>= 0``).

    Raises:
        AssertionError: If backend and model state diverge at any key or dir.
        ValueError: If ``steps`` is negative.
    """
    sut = _as_sut(factory.make())
    model = ModelFS()
    rng = SeededRandom(seed)
    program = _ops_for_seed(rng, steps=steps)
    for op, path, data in program:
        await _apply_to_model(model, op, path, data)
        await _apply_to_sut(sut, op, path, data)
    await assert_full_state_matches(sut, model)


async def assert_fork_isolation_if_local(factory: ResourceFactory) -> None:
    """A child fork's write is invisible to its parent (local backends only).

    Short-circuits (returns immediately) when
    ``factory.supports_local_fork_isolation()`` is ``False`` -- for remote /
    by-reference backends, isolation does NOT hold and asserting it would be
    wrong. For local content-backed resources (RAM copy-on-write, Disk eager
    copy) it verifies that:

      * a new key written only in the child is absent in the parent;
      * an inherited key overwritten in the child still reads its original
        value in the parent (structural sharing is correct, not a leak).

    The made resource must expose ``fork()`` (from ``ResourceLike``) returning
    a forked view that is itself a ``ResourceSUT``.

    Args:
        factory (ResourceFactory): Supplies a fresh backend under test.

    Raises:
        AssertionError: If a child write is observed in the parent, or an
            inherited key's parent value changed after a child overwrite.
        TypeError: If the made resource or its fork is not a ``ResourceSUT``.
    """
    if not factory.supports_local_fork_isolation():
        return
    parent = _as_sut(factory.make())
    inherited = "/inherited.bin"
    original = b"inherited-original"
    await parent.write(inherited, original)

    fork_fn = getattr(parent, "fork", None)
    if not callable(fork_fn):
        raise TypeError(
            f"[{factory.name}] resource view exposes no callable fork(); "
            "the consumer's adapter must surface ResourceLike.fork()"
        )
    child = _as_sut(fork_fn())

    child_only = "/child-only.bin"
    await child.write(child_only, b"child-secret")
    await child.write(inherited, b"child-overwrote")

    if await parent.exists(child_only):
        raise AssertionError(
            f"[{factory.name}] fork isolation broken: child-only key "
            f"{child_only!r} is visible in the parent"
        )
    parent_inherited = await parent.read(inherited)
    if parent_inherited != original:
        raise AssertionError(
            f"[{factory.name}] fork isolation broken: parent value of "
            f"{inherited!r} changed after child overwrite: "
            f"expected {original!r}, read {parent_inherited!r}"
        )


CONTRACT_CASES: "list[Callable[[ResourceFactory], Awaitable[None]]]" = [
    assert_write_read_roundtrip,
    assert_readdir_lists_children,
    assert_unlink_then_absent,
    assert_overwrite_replaces,
    assert_fork_isolation_if_local,
]


def contract_suite(
    factories: "Sequence[ResourceFactory]",
) -> "list[tuple[ResourceFactory, Callable[[ResourceFactory], Awaitable[None]]]]":
    """Build the ``(factory, case)`` cartesian product for parametrization.

    Returns argument tuples ONLY; the consumer owns the
    ``@pytest.mark.parametrize`` decorator and the (async) test stub so that
    the runtime ``mirage`` import stays in the consumer. ``assert_fault_free``
    is intentionally excluded from this product because it needs a ``seed``
    keyword and is wired separately by the consumer; the standard cases here
    take exactly one positional ``factory``.

    Args:
        factories (Sequence[ResourceFactory]): Concrete backend factories
            (e.g. RAM / Disk / fake-S3) supplied by the consumer.

    Returns:
        list[tuple[ResourceFactory, Callable]]: One tuple per
        ``(factory, case)`` pair, in stable factory-major order, suitable to
        splat into ``pytest.mark.parametrize("factory,case", contract_suite(...))``.
    """
    return [(factory, case) for factory in factories for case in CONTRACT_CASES]
