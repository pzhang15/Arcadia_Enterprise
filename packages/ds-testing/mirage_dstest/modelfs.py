"""Generic model-based oracle: a reference in-memory filesystem (the trivially
correct twin) plus differential assertion helpers comparing a system-under-test
against the model.

This module is engine-agnostic. It knows nothing about mirage and must import
cleanly with no mirage package installed. The ``SystemUnderTest`` Protocol is
the only coupling point; the mirage adapter (``adapters.py``) implements it.

Path convention:
    Every path is normalized to a single canonical form before use: a leading
    ``"/"`` is guaranteed, redundant ``"."`` / ``""`` segments are dropped, and
    trailing slashes are stripped (except for the root, which is always ``"/"``).
    File keys and directory keys live in the same normalized namespace. The root
    directory ``"/"`` always exists.

Fork semantics:
    ``ModelFS.fork()`` mirrors mirage ``RAMStore.fork``: it copies the ``files``
    dict and the ``dirs`` set (the lightweight key index) but shares the
    ``bytes`` payloads by reference. Because ``bytes`` are immutable, a write or
    unlink in one fork rebinds/pops a single key in that fork only and never
    affects the other fork. This is structural sharing, not a deep copy.

Soundness of the differential helpers:
    The ``assert_*`` helpers compare a live ``SystemUnderTest`` against the model
    and raise ``AssertionError`` (with the diverging path and both observed
    values) on any mismatch. They never swallow exceptions. A passing assertion
    means "no divergence witnessed for the probed paths", not a proof of global
    equivalence beyond what was probed.

Future-work seam (not implemented here):
    A later staged-write overlay reuses this oracle directly: ``commit(fork)``
    is modeled as a direct apply of the fork's ``snapshot()`` onto its parent,
    and ``abort(fork)`` as a no-op. Both drop in as helper functions over
    ``ModelFS.fork()`` + ``ModelFS.snapshot()`` with no new infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


def _normalize(path: str) -> str:
    """Normalize a path to its canonical form.

    Guarantees a leading ``"/"``, drops empty and ``"."`` segments, and strips a
    trailing slash. The root normalizes to ``"/"``.

    Args:
        path (str): A filesystem path; absolute or relative text is accepted.

    Returns:
        str: The canonical normalized path.
    """
    segments = [seg for seg in path.split("/") if seg not in ("", ".")]
    if not segments:
        return "/"
    return "/" + "/".join(segments)


def _parent(path: str) -> str:
    """Return the canonical parent directory of a normalized path.

    Args:
        path (str): An already-normalized path.

    Returns:
        str: The canonical parent path; the root's parent is the root.
    """
    if path == "/":
        return "/"
    head, _, _tail = path.rpartition("/")
    if head == "":
        return "/"
    return head


@dataclass
class ModelNode:
    files: dict[str, bytes] = field(default_factory=dict)
    dirs: set[str] = field(default_factory=lambda: {"/"})


@runtime_checkable
class SystemUnderTest(Protocol):
    async def read(self, path: str) -> bytes: ...

    async def exists(self, path: str) -> bool: ...

    async def readdir(self, path: str) -> list[str]: ...


class ModelFS:
    def __init__(self) -> None:
        """Create a fresh model filesystem containing only the root directory."""
        self._node = ModelNode()

    def write(self, path: str, data: bytes) -> None:
        """Write ``data`` at ``path``, creating ancestor directories as needed.

        Args:
            path (str): Destination path; normalized before use.
            data (bytes): File contents to bind to the key.
        """
        key = _normalize(path)
        self._node.files[key] = data
        self._ensure_ancestors(key)

    def read(self, path: str) -> bytes:
        """Return the bytes stored at ``path``.

        Args:
            path (str): Path to read; normalized before lookup.

        Returns:
            bytes: The file contents.

        Raises:
            KeyError: If no file exists at the normalized path.
        """
        key = _normalize(path)
        return self._node.files[key]

    def exists(self, path: str) -> bool:
        """Report whether a file or directory exists at ``path``.

        Args:
            path (str): Path to probe; normalized before lookup.

        Returns:
            bool: ``True`` if a file or directory key exists at the path.
        """
        key = _normalize(path)
        return key in self._node.files or key in self._node.dirs

    def unlink(self, path: str) -> None:
        """Remove the file at ``path``.

        Args:
            path (str): Path of the file to remove; normalized before lookup.

        Raises:
            KeyError: If no file exists at the normalized path.
        """
        key = _normalize(path)
        del self._node.files[key]

    def mkdir(self, path: str) -> None:
        """Create the directory at ``path`` and all ancestor directories.

        Args:
            path (str): Directory path to create; normalized before use.
        """
        key = _normalize(path)
        self._node.dirs.add(key)
        self._ensure_ancestors(key)

    def readdir(self, path: str) -> list[str]:
        """Return the sorted immediate child names of the directory at ``path``.

        Both child files and child subdirectories are listed by their final path
        component. Duplicate names (a file and a dir sharing a name) collapse to
        one entry.

        Args:
            path (str): Directory path to list; normalized before use.

        Returns:
            list[str]: Sorted immediate child names.
        """
        parent_key = _normalize(path)
        names: set[str] = set()
        for key in self._node.files:
            if _parent(key) == parent_key and key != parent_key:
                names.add(key.rsplit("/", 1)[-1])
        for key in self._node.dirs:
            if key == parent_key:
                continue
            if _parent(key) == parent_key:
                names.add(key.rsplit("/", 1)[-1])
        return sorted(names)

    def fork(self) -> "ModelFS":
        """Return a copy-on-write fork mirroring mirage ``RAMStore.fork``.

        Copies the ``files`` dict and the ``dirs`` set (the key index) while
        sharing the ``bytes`` payloads by reference. A write or unlink in either
        fork affects only that fork.

        Returns:
            ModelFS: An isolated child whose key index is independent of this
            instance but whose byte payloads are shared by reference.
        """
        child = ModelFS()
        child._node = ModelNode(
            files=dict(self._node.files),
            dirs=set(self._node.dirs),
        )
        return child

    def keys(self) -> set[str]:
        """Return the set of all file keys currently bound.

        Returns:
            set[str]: Every normalized file path present (directories excluded).
        """
        return set(self._node.files)

    def snapshot(self) -> dict[str, bytes]:
        """Return a deep, stable mapping of every file key to its bytes.

        Suitable for golden comparison. Because ``bytes`` are immutable, copying
        the dict is a sufficient deep snapshot of file state.

        Returns:
            dict[str, bytes]: A new dict mapping each file key to its contents.
        """
        return dict(self._node.files)

    def _ensure_ancestors(self, key: str) -> None:
        """Register every ancestor directory of ``key`` in the dirs index.

        Args:
            key (str): An already-normalized file or directory key.
        """
        current = _parent(key)
        while True:
            self._node.dirs.add(current)
            if current == "/":
                break
            current = _parent(current)


async def assert_read_matches(sut: SystemUnderTest, model: ModelFS, path: str) -> None:
    """Assert the SUT's bytes at ``path`` equal the model's.

    Args:
        sut (SystemUnderTest): The system under test.
        model (ModelFS): The reference oracle.
        path (str): Path to compare; normalized for the model lookup.

    Raises:
        AssertionError: If the SUT bytes differ from the model bytes, including
            the diverging path and both observed values.
    """
    expected = model.read(path)
    actual = await sut.read(path)
    if actual != expected:
        raise AssertionError(
            f"read mismatch at {path!r}: model={expected!r} sut={actual!r}"
        )


async def assert_dir_matches(sut: SystemUnderTest, model: ModelFS, path: str) -> None:
    """Assert the SUT's directory listing at ``path`` equals the model's.

    Both listings are compared as sorted lists of child names.

    Args:
        sut (SystemUnderTest): The system under test.
        model (ModelFS): The reference oracle.
        path (str): Directory path to compare; normalized for the model lookup.

    Raises:
        AssertionError: If the SUT listing differs from the model listing,
            including the diverging path and both observed listings.
    """
    expected = model.readdir(path)
    actual = sorted(await sut.readdir(path))
    if actual != expected:
        raise AssertionError(
            f"readdir mismatch at {path!r}: model={expected!r} sut={actual!r}"
        )


async def assert_full_state_matches(sut: SystemUnderTest, model: ModelFS) -> None:
    """Assert the SUT matches the model across every file key and every dir.

    For every file key in the model the SUT must report ``exists`` and identical
    bytes; for every directory in the model the SUT's listing must match. This is
    the periodic in-mem-twin-vs-real conformance gate.

    Args:
        sut (SystemUnderTest): The system under test.
        model (ModelFS): The reference oracle.

    Raises:
        AssertionError: On the first diverging file or directory, including the
            path and both observed values.
    """
    for key in sorted(model.keys()):
        if not await sut.exists(key):
            raise AssertionError(
                f"existence mismatch at {key!r}: model=True sut=False"
            )
        await assert_read_matches(sut, model, key)
    for directory in sorted(model._node.dirs):
        await assert_dir_matches(sut, model, directory)
