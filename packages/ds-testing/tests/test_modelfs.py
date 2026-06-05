"""Unit tests for the ModelFS oracle and its differential assert helpers."""

from __future__ import annotations

import pytest

from mirage_dstest.modelfs import (
    ModelFS,
    assert_dir_matches,
    assert_full_state_matches,
    assert_read_matches,
)


class _ModelBackedSUT:
    """A faithful SystemUnderTest that delegates straight to a ModelFS."""

    def __init__(self, model: ModelFS) -> None:
        self._model = model

    async def read(self, path: str) -> bytes:
        return self._model.read(path)

    async def exists(self, path: str) -> bool:
        return self._model.exists(path)

    async def readdir(self, path: str) -> list[str]:
        return self._model.readdir(path)


class _CorruptSUT(_ModelBackedSUT):
    """A wrong SUT: every read returns flipped bytes."""

    async def read(self, path: str) -> bytes:
        return self._model.read(path) + b"!corrupt"


def test_write_read_roundtrip_and_normalization() -> None:
    model = ModelFS()
    model.write("/a/b.txt", b"hello")
    assert model.read("a/b.txt") == b"hello"
    assert model.read("//a//b.txt") == b"hello"
    assert model.exists("/a")
    assert model.readdir("/a") == ["b.txt"]


def test_fork_shares_payload_but_isolates_index() -> None:
    parent = ModelFS()
    payload = b"shared-bytes"
    parent.write("/seed.txt", payload)
    child = parent.fork()
    assert child.read("/seed.txt") is payload
    child.write("/child.txt", b"c")
    assert not parent.exists("/child.txt")
    child.write("/seed.txt", b"overwritten")
    assert parent.read("/seed.txt") == payload
    parent.unlink("/seed.txt")
    assert child.read("/seed.txt") == b"overwritten"


def test_snapshot_is_stable_copy() -> None:
    model = ModelFS()
    model.write("/x", b"1")
    snap = model.snapshot()
    model.write("/x", b"2")
    assert snap["/x"] == b"1"


async def test_assert_helpers_pass_on_faithful_stub() -> None:
    model = ModelFS()
    model.write("/dir/a.txt", b"aaa")
    model.write("/dir/b.txt", b"bbb")
    sut = _ModelBackedSUT(model)
    await assert_read_matches(sut, model, "/dir/a.txt")
    await assert_dir_matches(sut, model, "/dir")
    await assert_full_state_matches(sut, model)


async def test_assert_read_fails_on_wrong_stub() -> None:
    model = ModelFS()
    model.write("/a.txt", b"data")
    sut = _CorruptSUT(model)
    with pytest.raises(AssertionError):
        await assert_read_matches(sut, model, "/a.txt")
    with pytest.raises(AssertionError):
        await assert_full_state_matches(sut, model)


async def test_assert_dir_fails_when_listing_diverges() -> None:
    model = ModelFS()
    model.write("/a.txt", b"x")
    extra = ModelFS()
    extra.write("/a.txt", b"x")
    extra.write("/ghost.txt", b"y")
    sut = _ModelBackedSUT(extra)
    with pytest.raises(AssertionError):
        await assert_dir_matches(sut, model, "/")
