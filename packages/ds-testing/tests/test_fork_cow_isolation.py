"""Differential model-based test of mirage ``Workspace.fork()`` COW isolation.

A :class:`DSStateMachine` drives an arbitrary fork DAG of live mirage
workspaces against a :class:`ModelFS` twin per node. Each node pairs a real
``Workspace`` (one RAM mount, seeded) with the trivially-correct in-memory
model that mirrors every write/unlink applied to that node. ``fork`` adds a
child node whose model is the parent model's COW fork; the invariant asserts
every node's live RAM-mount view byte-matches its model. A tiny name alphabet
and tiny payload alphabet force overwrites and re-creates across fork
boundaries, which is where a COW leak would surface.

Plus three explicit (non-Hypothesis) regression tests for the canonical
fork-isolation hazards: overwrite-of-inherited-key, nested-fork isolation, and
sibling-fork independence.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    initialize,
    invariant,
    rule,
)

from mirage.resource.ram import RAMResource
from mirage.types import DEFAULT_SESSION_ID, MountMode
from mirage.workspace import Workspace
from mirage_dstest.adapters import workspace_sut
from mirage_dstest.modelfs import ModelFS, assert_full_state_matches
from mirage_dstest.statemachine import DSStateMachine, run_machine

_MOUNT = "/ram"
_SEED_KEY = "/seed.txt"
_SEED_BYTES = b"seed\n"
_NAMES = ["a.txt", "b.txt", "c.txt"]
_TOKENS = [b"", b"x", b"yy", b"zzz"]


@dataclass
class _Node:
    ws: Workspace
    model: ModelFS


def _fresh_seeded_workspace() -> Workspace:
    """Build a workspace with one RAM mount seeded with the seed file.

    Returns:
        Workspace: A workspace whose ``/ram`` mount holds ``/seed.txt``.
    """
    ram = RAMResource()
    ram._store.files[_SEED_KEY] = _SEED_BYTES
    ws = Workspace({_MOUNT + "/": (ram, MountMode.EXEC)}, history=None)
    ws.get_session(DEFAULT_SESSION_ID).cwd = _MOUNT
    return ws


def _seeded_model() -> ModelFS:
    """Build the model twin matching a freshly seeded workspace.

    Returns:
        ModelFS: A model containing only ``/seed.txt``.
    """
    model = ModelFS()
    model.write(_SEED_KEY, _SEED_BYTES)
    return model


class ForkCOWIsolationMachine(DSStateMachine):
    """Drive a fork DAG of workspaces against per-node ModelFS twins."""

    nodes = Bundle("nodes")

    def __init__(self) -> None:
        self._all_nodes: list[_Node] = []
        super().__init__()

    async def setup_async(self) -> None:
        self._all_nodes = []

    async def teardown_async(self) -> None:
        for node in self._all_nodes:
            await node.ws.close()
        self._all_nodes = []

    @initialize(target=nodes)
    def root(self) -> _Node:
        node = _Node(ws=_fresh_seeded_workspace(), model=_seeded_model())
        self._all_nodes.append(node)
        return node

    @rule(target=nodes, parent=nodes)
    def fork(self, parent: _Node) -> _Node:
        child_ws = self._run(parent.ws.fork())
        child = _Node(ws=child_ws, model=parent.model.fork())
        self._all_nodes.append(child)
        return child

    @rule(
        node=nodes,
        name=st.sampled_from(_NAMES),
        token=st.sampled_from(_TOKENS),
    )
    def write(self, node: _Node, name: str, token: bytes) -> None:
        path = "/" + name
        sut = workspace_sut(node.ws, mount=_MOUNT)
        self._run(sut.write(path, token))
        node.model.write(path, token)

    @rule(node=nodes, name=st.sampled_from(_NAMES))
    def unlink(self, node: _Node, name: str) -> None:
        path = "/" + name
        if not node.model.exists(path):
            return
        sut = workspace_sut(node.ws, mount=_MOUNT)
        self._run(sut.unlink(path))
        node.model.unlink(path)

    @invariant()
    def every_node_matches_its_model(self) -> None:
        for node in self._all_nodes:
            sut = workspace_sut(node.ws, mount=_MOUNT)
            self._run(assert_full_state_matches(sut, node.model))


def test_fork_cow_isolation_stateful() -> None:
    seed_env = os.environ.get("DST_SEED")
    seed = int(seed_env, 0) if seed_env else 0xC0FFEE
    try:
        run_machine(
            ForkCOWIsolationMachine,
            seed=seed,
            max_examples=120,
            stateful_step_count=40,
        )
    except BaseException:
        print(f"\n[DST] fork-COW-isolation FAILED; replay with DST_SEED={seed}")
        raise


async def test_overwrite_of_inherited_key_isolated() -> None:
    parent = _fresh_seeded_workspace()
    child = await parent.fork()
    try:
        p = workspace_sut(parent, mount=_MOUNT)
        c = workspace_sut(child, mount=_MOUNT)
        await c.write(_SEED_KEY, b"CHILD-OVERWROTE")
        assert await c.read(_SEED_KEY) == b"CHILD-OVERWROTE"
        assert await p.read(_SEED_KEY) == _SEED_BYTES
    finally:
        await parent.close()
        await child.close()


async def test_nested_fork_grandchild_write_invisible() -> None:
    root = _fresh_seeded_workspace()
    child = await root.fork()
    grandchild = await child.fork()
    try:
        r = workspace_sut(root, mount=_MOUNT)
        c = workspace_sut(child, mount=_MOUNT)
        g = workspace_sut(grandchild, mount=_MOUNT)
        await g.write("/gc.txt", b"grandchild")
        assert await g.exists("/gc.txt")
        assert not await c.exists("/gc.txt")
        assert not await r.exists("/gc.txt")
    finally:
        await root.close()
        await child.close()
        await grandchild.close()


async def test_sibling_forks_independent() -> None:
    parent = _fresh_seeded_workspace()
    left = await parent.fork()
    right = await parent.fork()
    try:
        ls = workspace_sut(left, mount=_MOUNT)
        rs = workspace_sut(right, mount=_MOUNT)
        ps = workspace_sut(parent, mount=_MOUNT)
        await ls.write("/left.txt", b"L")
        await rs.write("/right.txt", b"R")
        assert await ls.exists("/left.txt")
        assert not await rs.exists("/left.txt")
        assert await rs.exists("/right.txt")
        assert not await ls.exists("/right.txt")
        assert not await ps.exists("/left.txt")
        assert not await ps.exists("/right.txt")
    finally:
        await parent.close()
        await left.close()
        await right.close()
