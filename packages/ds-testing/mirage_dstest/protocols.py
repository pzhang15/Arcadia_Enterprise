"""Structural typing surface for the mirage_dstest harness.

This module is the single place where mirage symbols are referenced, and they
are referenced ONLY under ``if TYPE_CHECKING:``. At runtime nothing here imports
mirage: ``PathSpecLike`` (and every other mirage-derived alias) resolves to
``typing.Any`` so the whole framework package is importable with no mirage
present. Sibling modules (chaos.py, modelfs.py, statemachine.py, contract.py)
type their parameters against the Protocols defined here; only adapters.py binds
them to concrete mirage objects at runtime.

Op-name table (the keys mirage ``Workspace.dispatch`` / ``BaseResource._ops``
expect — sourced from ``mirage.resource.ram.ram._RAM_OPS``). chaos.py and
adapters.py MUST agree on these exact strings:

    op key          -> mirage coroutine        notes
    --------------------------------------------------------------------------
    "read_bytes"    -> read_bytes              read a whole file as bytes
    "write"         -> write_bytes             CRITICAL: key is "write", not
                                               "write_bytes"
    "append"        -> append_bytes            CRITICAL: key is "append", not
                                               "append_bytes"
    "readdir"       -> readdir                 list child names
    "stat"          -> ram_stat / disk_stat    FileStat for a path
    "unlink"        -> unlink                  delete a single file
    "rmdir"         -> rmdir                   remove an empty directory
    "copy"          -> copy
    "rename"        -> rename
    "mkdir"         -> mkdir
    "read_stream"   -> read_stream             chunked async byte iterator
    "rm_recursive"  -> rm_r
    "du_total"      -> du
    "du_all"        -> du_all
    "create"        -> create                  create an empty file
    "truncate"      -> truncate
    "exists"        -> exists
    "find_flat"     -> find

So: the op key for writing is ``"write"`` (maps to ``write_bytes``), the op key
for appending is ``"append"`` (maps to ``append_bytes``), and reading is
``"read_bytes"``. ``ResourceOpProtocol`` mirrors the accessor-first sibling
signatures these coroutines expose once bound onto a resource.

Future seam (NOT implemented here, documented so it drops in without new infra):
a staged-write overlay would add op shapes ``stage(fork, path, data) ->
StageId`` / ``commit(fork)`` / ``abort(fork)``. ``modelfs.ModelFS`` already
backs the oracle via ``fork()`` + ``snapshot()``, so the later commit==
direct-apply and abort==no-op metamorphic relations slot in as plain helpers
over ModelFS. Only the seam is named now; no overlay code lives in this package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator, Protocol, runtime_checkable

if TYPE_CHECKING:
    from mirage.types import PathSpec  # noqa: F401

PathSpecLike = Any
"""Runtime alias for a mirage ``PathSpec``.

At runtime this is ``typing.Any`` so framework modules never import mirage. Under
``TYPE_CHECKING`` callers may annotate against ``mirage.types.PathSpec`` directly
(imported above); ``PathSpecLike`` exists for runtime-evaluated annotations and
for documenting intent without forcing the mirage import.
"""


@runtime_checkable
class AccessorLike(Protocol):
    """Marker protocol for a mirage accessor.

    The base mirage ``Accessor`` declares no async-method contract — concrete
    backend operations are dispatched through a resource's ``_ops`` table rather
    than declared on the accessor. This protocol is therefore intentionally a
    marker only; the harness never calls methods on it directly.
    """


@runtime_checkable
class ResourceOpProtocol(Protocol):
    """The per-op async surface a resource exposes (accessor already bound).

    These mirror the exact sibling mirage signatures that ``ChaosResource``
    wraps. The accessor is bound on the resource, so callers pass paths/data
    only. ``index`` is mirage's optional index-cache argument and is passed
    through opaquely.
    """

    async def read_bytes(self, path: PathSpecLike) -> bytes:
        """Read a whole file as bytes.

        Args:
            path (PathSpecLike): Target file path.
        """
        ...

    async def write(self, path: PathSpecLike, data: bytes) -> None:
        """Write bytes to a file, replacing existing content.

        Args:
            path (PathSpecLike): Target file path.
            data (bytes): Full file content to write.
        """
        ...

    async def readdir(self, path: PathSpecLike, index: Any) -> list[str]:
        """List the child names of a directory.

        Args:
            path (PathSpecLike): Directory path.
            index (Any): mirage index-cache handle (opaque, passed through).
        """
        ...

    async def stat(self, path: PathSpecLike, index: Any = None) -> Any:
        """Return file metadata for a path.

        Args:
            path (PathSpecLike): Target path.
            index (Any): mirage index-cache handle (opaque). Defaults to None.
        """
        ...

    async def unlink(self, path: PathSpecLike) -> None:
        """Delete a single file.

        Args:
            path (PathSpecLike): File path to remove.
        """
        ...

    async def read_stream(
        self, path: PathSpecLike, index: Any = None
    ) -> AsyncIterator[bytes]:
        """Stream a file as an async iterator of byte chunks.

        Args:
            path (PathSpecLike): File path to stream.
            index (Any): mirage index-cache handle (opaque). Defaults to None.
        """
        ...

    async def append(self, path: PathSpecLike, data: bytes) -> None:
        """Append bytes to the end of a file.

        Args:
            path (PathSpecLike): Target file path.
            data (bytes): Bytes to append.
        """
        ...

    async def create(self, path: PathSpecLike) -> None:
        """Create an empty file.

        Args:
            path (PathSpecLike): File path to create.
        """
        ...

    async def truncate(self, path: PathSpecLike, length: int) -> None:
        """Truncate a file to the given length.

        Args:
            path (PathSpecLike): Target file path.
            length (int): New file length in bytes.
        """
        ...

    async def exists(self, path: PathSpecLike) -> bool:
        """Report whether a path exists.

        Args:
            path (PathSpecLike): Path to probe.
        """
        ...


@runtime_checkable
class ResourceLike(Protocol):
    """The mirage ``BaseResource`` surface the chaos wrapper relies on.

    Attributes:
        name (str): Resource name (e.g. "ram", "disk").
        is_remote (bool): True for externally-owned backends (S3, Slack, ...).
            Destructive fault actions refuse to fire when this is True.
    """

    name: str
    is_remote: bool

    def fork(self) -> ResourceLike:
        """Return a forked resource per mirage fork semantics.

        RAM is copy-on-write, Disk eager-copies, remote shares by reference.
        """
        ...

    async def fingerprint(self, path: str) -> str | None:
        """Return a change-detection fingerprint for a path, or None.

        Args:
            path (str): Target path.
        """
        ...


@runtime_checkable
class WorkspaceLike(Protocol):
    """The mirage ``Workspace`` surface the adapters seam drives.

    ``dispatch`` returns ``tuple[Any, Any]`` mirroring mirage's
    ``tuple[value, IOResult]``; callers unpack index ``[0]`` for the value.
    """

    async def dispatch(
        self, op: str, path: PathSpecLike, **kwargs: Any
    ) -> tuple[Any, Any]:
        """Dispatch an op-name against a path, returning (value, io_result).

        Args:
            op (str): An op-name key from the module-level op-name table
                (e.g. "read_bytes", "write", "append", "unlink").
            path (PathSpecLike): Target path (a mirage PathSpec at runtime).
            **kwargs (Any): Op-specific keyword arguments (e.g. data=...).
        """
        ...

    async def fork(self) -> WorkspaceLike:
        """Return a forked workspace (COW for RAM/cache, eager for Disk)."""
        ...

    async def stat(self, path: str) -> Any:
        """Return file metadata for a path.

        Args:
            path (str): Target path (mirage wraps it in a PathSpec internally).
        """
        ...

    async def readdir(self, path: str) -> list[str]:
        """List child names of a directory.

        Args:
            path (str): Directory path.
        """
        ...

    async def close(self) -> None:
        """Close the workspace, releasing drain tasks and cache."""
        ...
