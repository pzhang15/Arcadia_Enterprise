"""Runtime mirage-coupling shims for the deterministic-simulation harness.

This is the ONE module that imports mirage at module load time
(``from mirage.types import PathSpec``; ``from mirage.resource.base import
BaseResource``). Importing it therefore requires mirage to be installed.
For that reason it is deliberately NOT re-exported from ``__init__.py`` and
consumers import it explicitly only when running against a real mirage.

Op-name mapping. The harness model op-names map to the mirage VFS op-names
that ``Workspace.dispatch`` actually resolves (the ``@op(...)`` names
registered on the mount), which differ from the ``BaseResource._ops`` keys
used by attribute access:

    model 'write'         -> dispatch 'write'   (mirage core write_bytes)
    model 'append'        -> dispatch 'append'  (mirage core append_bytes)
    model 'read'          -> dispatch 'read'    (NOT 'read_bytes' — the
                                                 registered VFS op is 'read')
    model 'delete'/'unlink' -> dispatch 'unlink'

The ChaosResource method surface (from the blueprint) is named
``read_bytes``; ``_VFS_OP_TO_CHAOS`` reconciles the VFS op-name ``read``
with the chaos method ``read_bytes``.

``Workspace.dispatch(op, path, **kwargs)`` returns ``tuple[Any, IOResult]``;
the value is element ``[0]``.

Dispatch routing of faults: mirage routes an op through
``Mount.execute_op``, which calls the mount's registered
``RegisteredOp.fn`` as ``fn(resource.accessor, scope, *args, **kwargs)``
(the ops are resolved from ``resource.ops_list()`` at mount-build time, not
from ``BaseResource._ops``). ``wrap_chaos`` therefore returns a
``BaseResource`` subclass whose ``ops_list()`` yields ``RegisteredOp``s
whose ``fn`` routes through an internal ``ChaosResource`` before performing
the real op, and whose ``_ops`` instance dict is re-pointed at the same
gated callables so direct attribute access is gated too.
name / is_remote / fingerprint / accessor / index / fork are preserved
from the wrapped resource.

Paths crossing into mirage are always wrapped in ``PathSpec`` via
``PathSpec.from_str_path`` (never a raw ``str`` — CLAUDE.md type rule).
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable

from mirage.resource.base import BaseResource
from mirage.types import PathSpec
from mirage_dstest.chaos import ChaosResource, FaultSchedule
from mirage_dstest.clock import VirtualClock

if TYPE_CHECKING:
    from mirage_dstest.modelfs import SystemUnderTest
    from mirage_dstest.protocols import WorkspaceLike

_OP_WRITE = "write"
_OP_APPEND = "append"
_OP_READ = "read"
_OP_UNLINK = "unlink"

_MODEL_OP_TO_DISPATCH = {
    "write": _OP_WRITE,
    "append": _OP_APPEND,
    "unlink": _OP_UNLINK,
    "delete": _OP_UNLINK,
}

# Maps a mirage VFS op-name (the @op(...) name resolved by
# Mount.execute_op / Workspace.dispatch) to the ChaosResource method that
# gates it. The blueprint's ChaosResource exposes 'read_bytes', but the
# registered VFS read op is named 'read' (there is no registered
# 'read_bytes'/'read_stream' VFS op for RAM/Disk); this is the single place
# the two naming worlds are reconciled.
_VFS_OP_TO_CHAOS = {
    "read": "read_bytes",
    "write": "write",
    "append": "append",
    "unlink": "unlink",
    "readdir": "readdir",
    "stat": "stat",
}

_CHAOS_GATED_OPS = frozenset(_VFS_OP_TO_CHAOS)


class _PathSpecHelper:
    """Convert ``str`` paths into mirage ``PathSpec`` at the boundary.

    Keeps raw ``str`` paths from leaking into mirage (CLAUDE.md type rule):
    every string that crosses into a mirage call is wrapped here.
    """

    @staticmethod
    def of(path: str, prefix: str = "") -> PathSpec:
        """Wrap a string path as a ``PathSpec``.

        Args:
            path (str): Absolute virtual path (already mount-joined).
            prefix (str): Optional mount prefix carried on the spec.

        Returns:
            PathSpec: A resolved path spec for the given string.
        """
        return PathSpec.from_str_path(path, prefix=prefix)


def _join_mount(mount: str, path: str) -> str:
    """Join a mount prefix and a relative path into an absolute VFS path.

    Args:
        mount (str): Mount prefix (e.g. ``"/"`` or ``"/data"``).
        path (str): Path relative to the mount or already absolute.

    Returns:
        str: A normalized absolute path under ``mount``.
    """
    base = "/" + mount.strip("/")
    rest = path.lstrip("/")
    if base == "/":
        return "/" + rest
    if rest == "":
        return base
    return base + "/" + rest


async def _unwrap_dispatch(ws: "WorkspaceLike", op: str, spec: PathSpec,
                           **kwargs: Any) -> Any:
    """Dispatch a mirage op and return the value, discarding the IOResult.

    Args:
        ws (WorkspaceLike): The workspace to dispatch on.
        op (str): Mirage VFS op name (e.g. ``"read"``, ``"write"``).
        spec (PathSpec): Path spec for the op.
        **kwargs (Any): Extra op kwargs (e.g. ``data``).

    Returns:
        Any: The value element of the ``(value, IOResult)`` tuple.
    """
    result = await ws.dispatch(op, spec, **kwargs)
    return result[0]


class _WorkspaceSUT:
    """A ``SystemUnderTest`` view over a mirage ``Workspace`` + mount prefix.

    Implements the differential-oracle surface (``read``/``exists``/
    ``readdir``) plus the mutation surface (``write``/``unlink``) by
    dispatching mirage ops with correctly wrapped ``PathSpec`` paths.
    ``read`` -> ``dispatch('read')``; ``write`` -> ``dispatch('write')``;
    ``unlink`` -> ``dispatch('unlink')``; ``readdir`` -> ``ws.readdir``;
    ``exists`` -> a ``stat`` probe (absent -> False).

    ``readdir`` returns BASENAMES: mirage's RAM readdir yields absolute,
    mount-prefixed paths (e.g. ``/ram/a.txt``) but the ``modelfs`` oracle
    compares final path components, so each entry is reduced to its last
    segment here.
    """

    def __init__(self, ws: "WorkspaceLike", mount: str) -> None:
        self._ws = ws
        self._mount = mount

    def _abs(self, path: str) -> str:
        return _join_mount(self._mount, path)

    async def read(self, path: str) -> bytes:
        """Read raw bytes at ``path`` (relative to the mount).

        Args:
            path (str): Path relative to the configured mount prefix.

        Returns:
            bytes: The file contents.
        """
        spec = _PathSpecHelper.of(self._abs(path))
        return await _unwrap_dispatch(self._ws, _OP_READ, spec)

    async def write(self, path: str, data: bytes) -> None:
        """Write ``data`` at ``path`` (relative to the mount).

        Args:
            path (str): Path relative to the configured mount prefix.
            data (bytes): Full file contents to write (replaces existing).
        """
        spec = _PathSpecHelper.of(self._abs(path))
        await _unwrap_dispatch(self._ws, _OP_WRITE, spec, data=data)

    async def unlink(self, path: str) -> None:
        """Delete the file at ``path`` (relative to the mount).

        Args:
            path (str): Path relative to the configured mount prefix.
        """
        spec = _PathSpecHelper.of(self._abs(path))
        await _unwrap_dispatch(self._ws, _OP_UNLINK, spec)

    async def exists(self, path: str) -> bool:
        """Report whether ``path`` exists via a ``stat`` probe.

        Args:
            path (str): Path relative to the configured mount prefix.

        Returns:
            bool: True if a stat succeeds, False if the file is absent.
        """
        try:
            await self._ws.stat(self._abs(path))
        except (FileNotFoundError, KeyError):
            return False
        return True

    async def readdir(self, path: str) -> list[str]:
        """List immediate child basenames under ``path``.

        Args:
            path (str): Directory path relative to the mount prefix.

        Returns:
            list[str]: Child basenames (final path components).
        """
        raw = await self._ws.readdir(self._abs(path))
        return [entry.rstrip("/").rsplit("/", 1)[-1] for entry in raw]


def workspace_sut(ws: "WorkspaceLike", *,
                  mount: str = "/") -> "SystemUnderTest":
    """Build a ``SystemUnderTest`` over a mirage workspace + mount prefix.

    Args:
        ws (WorkspaceLike): The mirage ``Workspace`` to wrap.
        mount (str): Mount prefix whose subtree the oracle observes.

    Returns:
        SystemUnderTest: A read/exists/readdir view dispatching to ``ws``.
    """
    return _WorkspaceSUT(ws, mount)


async def _resource_execute_op(resource: BaseResource, op_name: str,
                               path: str, *args: Any) -> Any:
    """Execute a registered VFS op on a bare resource (no mount).

    Resolves the filetype-agnostic ``RegisteredOp`` for ``op_name`` from the
    resource's ``ops_list()`` and calls its ``fn`` exactly as
    ``Mount.execute_op`` would (accessor first, a ``PathSpec`` scope, then the
    op args, with ``index`` supplied), awaiting the result.

    Args:
        resource (BaseResource): The concrete resource to drive.
        op_name (str): The VFS op name (e.g. ``"read"``, ``"write"``).
        path (str): Absolute backend path (leading slash).
        *args (Any): Positional op args after the path (e.g. ``data`` for
            ``write``).

    Returns:
        Any: The op result.

    Raises:
        AttributeError: If the resource has no filetype-agnostic op of that
            name.
    """
    fn: Callable[..., Any] | None = None
    for ro in resource.ops_list():
        if ro.name == op_name and ro.filetype is None:
            fn = ro.fn
            break
    if fn is None:
        raise AttributeError(f"{resource.name}: no op {op_name!r}")
    spec = PathSpec(
        original=path,
        directory=path.rsplit("/", 1)[0] or "/",
        prefix="",
    )
    result = fn(resource.accessor, spec, *args, index=resource.index)
    if hasattr(result, "__await__"):
        return await result
    return result


class _ResourceSUT:
    """A ``ResourceSUT`` view over a bare mirage ``BaseResource``.

    Drives a single concrete resource (RAM / Disk / a local fake) directly
    through its registered VFS ops, bypassing ``Workspace`` and the cache so
    the resource's own ``fork()`` semantics can be exercised end-to-end by
    ``contract.assert_fork_isolation_if_local``. ``fork()`` is synchronous and
    returns another ``_ResourceSUT`` over the resource's forked view (RAM is
    copy-on-write, Disk eager-copies, remote shares by reference). ``readdir``
    is reduced to basenames to match the ``modelfs`` oracle.

    Args:
        resource (BaseResource): The concrete resource to wrap.
    """

    def __init__(self, resource: BaseResource) -> None:
        self._resource = resource
        self.name = getattr(resource, "name", "resource")

    async def read(self, path: str) -> bytes:
        """Read raw bytes at ``path``.

        Args:
            path (str): Absolute backend path.

        Returns:
            bytes: The file contents.
        """
        return await _resource_execute_op(self._resource, _OP_READ, path)

    async def write(self, path: str, data: bytes) -> None:
        """Write ``data`` at ``path`` (replacing existing content).

        Args:
            path (str): Absolute backend path.
            data (bytes): Full file contents to write.
        """
        await _resource_execute_op(self._resource, _OP_WRITE, path, data)

    async def unlink(self, path: str) -> None:
        """Delete the file at ``path``.

        Args:
            path (str): Absolute backend path.
        """
        await _resource_execute_op(self._resource, _OP_UNLINK, path)

    async def exists(self, path: str) -> bool:
        """Report whether ``path`` exists via a ``stat`` probe.

        Args:
            path (str): Absolute backend path.

        Returns:
            bool: True if a stat succeeds, False if the file is absent.
        """
        try:
            await _resource_execute_op(self._resource, "stat", path)
        except (FileNotFoundError, KeyError):
            return False
        return True

    async def readdir(self, path: str) -> list[str]:
        """List immediate child basenames under ``path``.

        Args:
            path (str): Absolute directory path.

        Returns:
            list[str]: Child basenames (final path components).
        """
        raw = await _resource_execute_op(self._resource, "readdir", path)
        return [entry.rstrip("/").rsplit("/", 1)[-1] for entry in raw]

    def fork(self) -> "_ResourceSUT":
        """Fork the wrapped resource and wrap the child.

        Returns:
            _ResourceSUT: A SUT over ``resource.fork()`` (COW for RAM, eager
            copy for Disk, share-by-reference for remote).
        """
        return _ResourceSUT(self._resource.fork())


class LocalResourceFactory:
    """A ``contract.ResourceFactory`` over a local content-backed resource.

    ``make()`` returns a fresh :class:`_ResourceSUT` from a zero-argument
    resource constructor (e.g. ``RAMResource``). Declares local fork isolation
    so ``contract.assert_fork_isolation_if_local`` runs its body rather than
    short-circuiting; pass ``supports_fork_isolation=False`` for a
    remote/by-reference backend.

    Args:
        name (str): Backend label used in parametrization ids.
        resource_factory (Callable[[], BaseResource]): Zero-arg constructor for
            a fresh concrete resource.
        supports_fork_isolation (bool): Whether the backend's ``fork()``
            isolates a child's writes from its parent (True for RAM/Disk).
    """

    def __init__(self, name: str,
                 resource_factory: Callable[[], BaseResource], *,
                 supports_fork_isolation: bool = True) -> None:
        self.name = name
        self._resource_factory = resource_factory
        self._supports_fork_isolation = supports_fork_isolation

    def make(self) -> Any:
        """Build a fresh resource-backed SUT.

        Returns:
            Any: A :class:`_ResourceSUT` over a new resource instance.
        """
        return _ResourceSUT(self._resource_factory())

    def supports_local_fork_isolation(self) -> bool:
        """Report whether this backend's fork isolates child writes.

        Returns:
            bool: The configured isolation flag.
        """
        return self._supports_fork_isolation


async def model_apply_to_workspace(ws: "WorkspaceLike", op: str, path: str, *,
                                   data: bytes | None = None) -> None:
    """Apply a model-level mutation to a mirage workspace.

    The canonical writer shared by the contract suite and the state-machine
    rules. Maps the model op-name to the mirage dispatch op-name and wraps
    the path in a ``PathSpec`` before dispatching.

    Args:
        ws (WorkspaceLike): The workspace to mutate.
        op (str): Model op name: ``"write"``, ``"append"``, or
            ``"unlink"``/``"delete"``.
        path (str): Absolute virtual path to mutate.
        data (bytes | None): Payload for ``write``/``append``; must be
            provided for those ops and must be None for ``unlink``.

    Raises:
        ValueError: If ``op`` is unknown, or ``data`` is missing for a
            write/append, or supplied for an unlink.
    """
    dispatch_op = _MODEL_OP_TO_DISPATCH.get(op)
    if dispatch_op is None:
        raise ValueError(f"unknown model op: {op!r}")
    spec = _PathSpecHelper.of(path)
    if dispatch_op in (_OP_WRITE, _OP_APPEND):
        if data is None:
            raise ValueError(f"op {op!r} requires data")
        await _unwrap_dispatch(ws, dispatch_op, spec, data=data)
        return
    if data is not None:
        raise ValueError(f"op {op!r} does not take data")
    await _unwrap_dispatch(ws, dispatch_op, spec)


class _BoundOpResource:
    """A ``ResourceLike`` whose ops invoke mirage op fns bound to an accessor.

    Used internally as the ``inner`` of a :class:`ChaosResource`: each op
    method looks up the original ``RegisteredOp.fn`` for that op-name and
    calls it as ``fn(accessor, path, *args, **kwargs)`` — exactly how
    ``Mount.execute_op`` would. This lets the chaos fault gate sit in
    front of the real, unmodified mirage op while keeping every chaos
    semantic in ``chaos.py`` (the single source of truth).
    """

    def __init__(self, resource: BaseResource,
                 op_fns: dict[str, Callable[..., Any]]) -> None:
        self._resource = resource
        self._op_fns = dict(op_fns)
        self.name = getattr(resource, "name", "base")
        self.is_remote = bool(getattr(resource, "is_remote", False))

    @property
    def accessor(self) -> Any:
        return self._resource.accessor

    def _fn(self, op: str) -> Callable[..., Any]:
        fn = self._op_fns.get(op)
        if fn is None:
            raise AttributeError(
                f"{self.name}: no op {op!r} on wrapped resource")
        return fn

    def _index_for(self, override: Any) -> Any:
        if override is not None:
            return override
        return getattr(self._resource, "index", None)

    async def _call(self, op: str, path: Any, *args: Any,
                    **kwargs: Any) -> Any:
        fn = self._fn(op)
        kwargs.setdefault("index", getattr(self._resource, "index", None))
        result = fn(self._resource.accessor, path, *args, **kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result

    def fork(self) -> "_BoundOpResource":
        """Fork the wrapped resource and rebind op fns to the child.

        Returns:
            _BoundOpResource: A bound-op shim over ``resource.fork()``.
        """
        child = self._resource.fork()
        return _BoundOpResource(child, self._op_fns)

    async def fingerprint(self, path: str) -> str | None:
        """Delegate fingerprinting to the wrapped resource.

        Args:
            path (str): Backend-relative path.

        Returns:
            str | None: The resource fingerprint, or None.
        """
        return await self._resource.fingerprint(path)

    async def read_bytes(self, path: Any) -> bytes:
        return await self._call("read_bytes", path)

    async def write(self, path: Any, data: bytes) -> None:
        await self._call("write", path, data)

    async def append(self, path: Any, data: bytes) -> None:
        await self._call("append", path, data)

    async def unlink(self, path: Any) -> None:
        await self._call("unlink", path)

    async def readdir(self, path: Any, index: Any = None) -> list[str]:
        if index is None:
            return await self._call("readdir", path)
        return await self._call("readdir", path, index=index)

    async def stat(self, path: Any, index: Any = None) -> Any:
        if index is None:
            return await self._call("stat", path)
        return await self._call("stat", path, index=index)

    async def read_stream(self, path: Any,
                          index: Any = None) -> AsyncIterator[bytes]:
        if index is None:
            return await self._call("read_stream", path)
        return await self._call("read_stream", path, index=index)


class _GatedOpFn:
    """A ``RegisteredOp.fn``-shaped callable routing through a chaos op.

    Instances match mirage's op-fn convention
    ``fn(accessor, scope, *args, **kwargs)``; the ``accessor`` and any
    ``index`` kwarg are dropped (the chaos inner already holds the
    accessor), and the scope + remaining op args forward to the gated
    chaos coroutine. The VFS op-name is translated to the chaos method name
    via ``_VFS_OP_TO_CHAOS``. A callable class (not a nested ``def``) so
    the no-nested-functions rule holds.
    """

    def __init__(self, chaos: ChaosResource, vfs_op: str) -> None:
        chaos_name = _VFS_OP_TO_CHAOS.get(vfs_op, vfs_op)
        self._method = _chaos_op_for(chaos, chaos_name)
        self.__name__ = f"chaos_{vfs_op}"

    async def __call__(self, accessor: Any, scope: Any, *args: Any,
                       **kwargs: Any) -> Any:
        kwargs.pop("index", None)
        return await self._method(scope, *args, **kwargs)


class _OpsListReturner:
    """A callable assigned as the wrapper's ``ops_list`` attribute.

    Returns a precomputed gated ``RegisteredOp`` list. It is set as an
    INSTANCE/class attribute (a plain object, not a function), so normal
    attribute lookup returns this object directly and ``ops_list()`` calls
    ``__call__`` with no implicit ``self`` — the object already captures
    everything it needs. A callable class (not a lambda) keeps the
    no-nested-functions rule.
    """

    def __init__(self, ops: list[Any]) -> None:
        self._ops = ops

    def __call__(self) -> list[Any]:
        return self._ops


class _WrappedFingerprint:
    """A callable assigned as the wrapper's ``fingerprint`` attribute.

    Delegates to the wrapped resource; set as a plain attribute so the call
    receives no implicit ``self``.
    """

    def __init__(self, inner: BaseResource) -> None:
        self._inner = inner

    async def __call__(self, path: str) -> str | None:
        return await self._inner.fingerprint(path)


class _WrapperFork:
    """A callable assigned as the wrapper's ``fork`` attribute.

    Delegates to :meth:`ChaosResource.fork`, which forks both the inner
    resource and the fault schedule's seeded sub-stream, then re-wraps the
    forked inner as a fresh ``BaseResource`` subclass. Set as a plain
    attribute so the call receives no implicit ``self``.
    """

    def __init__(self, inner: BaseResource, chaos: ChaosResource,
                 clock: VirtualClock) -> None:
        self._inner = inner
        self._chaos = chaos
        self._clock = clock

    def __call__(self) -> BaseResource:
        child_chaos = self._chaos.fork()
        child_inner = self._inner.fork()
        return _wrap_with_chaos(child_inner, child_chaos, self._clock)


def _chaos_op_for(chaos: ChaosResource, op: str) -> Callable[..., Any]:
    """Return the ChaosResource coroutine method implementing ``op``.

    Args:
        chaos (ChaosResource): The fault-injecting wrapper instance.
        op (str): Mirage op name to route through the gate.

    Returns:
        Callable[..., Any]: The bound chaos op method.

    Raises:
        AttributeError: If the chaos wrapper has no such op.
    """
    method = getattr(chaos, op, None)
    if method is None:
        raise AttributeError(f"ChaosResource has no op {op!r}")
    return method


def _collect_op_fns(resource: BaseResource) -> dict[str, Callable[..., Any]]:
    """Map ChaosResource-method-name -> original op fn for a resource.

    Only the general (filetype-agnostic) registered ops are taken, and
    their VFS op-name is translated to the chaos method name via
    ``_VFS_OP_TO_CHAOS`` so the internal :class:`_BoundOpResource` can look
    a fn up under the same name its op method uses (e.g. its ``read_bytes``
    method finds the original ``read`` op fn).

    Args:
        resource (BaseResource): A concrete mirage resource.

    Returns:
        dict[str, Callable[..., Any]]: Op fns keyed by chaos method name.
    """
    fns: dict[str, Callable[..., Any]] = {}
    for ro in resource.ops_list():
        if ro.filetype is not None:
            continue
        chaos_name = _VFS_OP_TO_CHAOS.get(ro.name, ro.name)
        fns[chaos_name] = ro.fn
    return fns


def _gated_ops_list(resource: BaseResource,
                    chaos: ChaosResource) -> list[Any]:
    """Build the chaos-gated ``RegisteredOp`` list for a wrapped resource.

    Each general op the chaos wrapper can gate is rebound to a
    :class:`_GatedOpFn` via :func:`dataclasses.replace`; non-gated ops
    (copy/rename/mkdir/du/...) keep their original fn so the resource stays
    fully functional.

    Args:
        resource (BaseResource): The wrapped concrete resource.
        chaos (ChaosResource): The fault-injecting wrapper.

    Returns:
        list[Any]: RegisteredOp objects suitable for mount registration.
    """
    out: list[Any] = []
    for ro in resource.ops_list():
        if ro.filetype is None and ro.name in _CHAOS_GATED_OPS:
            out.append(dataclasses.replace(ro, fn=_GatedOpFn(chaos, ro.name)))
        else:
            out.append(ro)
    return out


def _gated_op_dict(resource: BaseResource,
                   chaos: ChaosResource) -> dict[str, Callable[..., Any]]:
    """Map op-name -> gated fn for re-pointing a resource's ``_ops`` dict.

    Args:
        resource (BaseResource): The wrapped concrete resource.
        chaos (ChaosResource): The fault-injecting wrapper.

    Returns:
        dict[str, Callable[..., Any]]: Gated op fns keyed by op name.
    """
    out: dict[str, Callable[..., Any]] = {}
    for ro in resource.ops_list():
        if ro.filetype is None and ro.name in _CHAOS_GATED_OPS:
            out[ro.name] = _GatedOpFn(chaos, ro.name)
    return out


def _wrap_with_chaos(inner: BaseResource, chaos: ChaosResource,
                     clock: VirtualClock) -> BaseResource:
    """Build the chaos-wrapping subclass instance around ``inner``+``chaos``.

    Args:
        inner (BaseResource): The concrete resource being wrapped.
        chaos (ChaosResource): The fault-injecting wrapper over ``inner``.
        clock (VirtualClock): The virtual clock (threaded into forks).

    Returns:
        BaseResource: A subclass instance of ``type(inner)`` whose op
        surface is gated by ``chaos``.
    """
    base_cls = type(inner)
    wrapper_cls = type(f"Chaos{base_cls.__name__}", (base_cls,), {})

    wrapped = wrapper_cls.__new__(wrapper_cls)
    wrapped.__dict__.update(inner.__dict__)
    wrapped.name = inner.name
    wrapped.is_remote = inner.is_remote
    wrapped._ops = {**dict(getattr(base_cls, "_ops", {})),
                    **_gated_op_dict(inner, chaos)}
    wrapped.ops_list = _OpsListReturner(_gated_ops_list(inner, chaos))
    wrapped.fork = _WrapperFork(inner, chaos, clock)
    wrapped.fingerprint = _WrappedFingerprint(inner)
    return wrapped


def wrap_chaos(inner: BaseResource, schedule: FaultSchedule,
               clock: VirtualClock) -> BaseResource:
    """Wrap a concrete resource so mirage dispatch routes through faults.

    Returns an instance of a fresh ``BaseResource`` subclass that shares
    the wrapped resource's accessor/store/index and whose op surface is
    gated by a :class:`ChaosResource`. Because ``ops_list()`` is overridden
    to return chaos-gated ``RegisteredOp``s, mounting the returned resource
    makes ``Workspace.dispatch('write', ...)`` flow through the fault gate;
    ``_ops`` is re-pointed at the same gated callables for direct attribute
    access. ``name``/``is_remote``/``fingerprint``/``fork`` are preserved.

    Args:
        inner (BaseResource): The concrete mirage resource to wrap.
        schedule (FaultSchedule): The seeded fault schedule to apply.
        clock (VirtualClock): The virtual clock used for delay faults.

    Returns:
        BaseResource: A chaos-wrapping subclass instance of ``type(inner)``.
    """
    op_fns = _collect_op_fns(inner)
    bound = _BoundOpResource(inner, op_fns)
    chaos = ChaosResource(bound, schedule, clock)
    return _wrap_with_chaos(inner, chaos, clock)
