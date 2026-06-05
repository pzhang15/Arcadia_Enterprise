import asyncio
import json
import os
import time

import server
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import create_async_engine

from arcadia_store.models import runs, steps, stream_events, tool_calls, vfs_ops


class _Delta:
    def __init__(self, content=None, reasoning_content=None):
        self.content = content
        self.reasoning_content = reasoning_content


class _Chunk:
    def __init__(self, delta):
        self.choices = [type("C", (), {"delta": delta})()]


class _Stream:
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        return self._gen()

    async def _gen(self):
        for c in self._chunks:
            yield c


class _MultiTurnClient:
    """Fake AsyncOpenAI that returns a different streamed turn per create() call."""

    def __init__(self, turns):
        self._turns = list(turns)
        self._i = 0
        completions = type("Comp", (), {"create": self._create})()
        self.chat = type("Chat", (), {"completions": completions})()

    async def _create(self, **kwargs):
        turn = self._turns[min(self._i, len(self._turns) - 1)]
        self._i += 1
        return _Stream([_Chunk(d) for d in turn])


# Turn 1: reasoning, then an EXEC command. Turn 2: final answer (no EXEC -> stop).
_TURNS = [
    [
        _Delta(reasoning_content="I should record a probe file "),
        _Delta(reasoning_content="to see what is available."),
        _Delta(content="Let me record a probe.\n"
               "EXEC: echo arcadia-e2e > /e2e_probe.txt\n"),
    ],
    [
        _Delta(content="I wrote the probe to the workspace. Done."),
    ],
]


def _parse_sse(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                out.append(json.loads(payload))
    return out


def _wait_for(predicate, timeout: float = 6.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.1)
    return predicate()


async def _count_rows(conn, table, column, value) -> int:
    res = await conn.execute(
        select(func.count()).select_from(table).where(column == value))
    return res.scalar()


async def _derived_counts(dsn: str, sid: str) -> dict:
    engine = create_async_engine(dsn)
    try:
        async with engine.connect() as conn:
            return {
                "runs": await _count_rows(conn, runs, runs.c.session_id, sid),
                "steps": await _count_rows(conn, steps, steps.c.session_id, sid),
                "tool_calls": await _count_rows(
                    conn, tool_calls, tool_calls.c.session_id, sid),
                "vfs_ops": await _count_rows(
                    conn, vfs_ops, vfs_ops.c.session_id, sid),
                "stream": await _count_rows(
                    conn, stream_events, stream_events.c.session, sid),
            }
    finally:
        await engine.dispose()


def test_full_agent_turn_persists_and_rehydrates(client, monkeypatch):
    monkeypatch.setattr(server, "OPENAI_API_KEY", "test")
    monkeypatch.setattr(server, "_get_openai_client",
                        lambda: _MultiTurnClient(_TURNS))

    created = client.post("/api/sessions", json={"services": ["it"]}).json()
    sid = created["id"]
    has_workspace = created["has_workspace"]

    resp = client.post(f"/api/sessions/{sid}/message/stream",
                       json={"message": "triage open IT tickets"})
    assert resp.status_code == 200, resp.text
    live = _parse_sse(resp.text)
    live_types = {e["type"] for e in live}

    # The live stream carries reasoning, an answer, a tool call + result, and run end.
    assert "THINKING_START" in live_types
    assert "THINKING_CONTENT" in live_types
    assert "TEXT_MESSAGE_CONTENT" in live_types
    assert "TOOL_CALL_START" in live_types
    assert "TOOL_CALL_RESULT" in live_types
    assert "RUN_FINISHED" in live_types
    reasoning = "".join(e.get("delta", "") for e in live
                        if e["type"] == "THINKING_CONTENT")
    assert "available" in reasoning
    live_vfs = [e for e in live
                if e["type"] == "CUSTOM" and e.get("name") == "vfs_op"]
    if has_workspace:
        # Writing to the RAM-backed root records a VFS write op.
        assert live_vfs, "expected a vfs_op for the write command"
        # Phase-0 correlation: every vfs_op is stamped with the tool call
        # that caused it, plus the source field that used to be dropped.
        tc_ids = {e["tool_call_id"] for e in live
                  if e["type"] == "TOOL_CALL_START"}
        for vop in live_vfs:
            value = vop["value"]
            assert value.get("tool_call_id") in tc_ids, (
                "vfs_op not correlated to its causing tool call")
            assert value.get("run_id"), "vfs_op missing run_id"
            assert "source" in value, "vfs_op missing restored source field"

    # Simulate a restart: drop the in-memory session, then hydrate from the DB.
    def _evict_and_fetch():
        server._sessions.pop(sid, None)
        r = client.get(f"/api/sessions/{sid}/trace")
        if r.status_code != 200:
            return None
        body = r.json()
        types = [e["type"] for e in body["events"]]
        return body if "RUN_FINISHED" in types else None

    trace = _wait_for(_evict_and_fetch)
    assert trace is not None, "agent trace did not persist for hydration"
    rehydrated = [e["type"] for e in trace["events"]]
    # Coalesced trace replays the same shape as the live stream.
    for expected in ("RUN_STARTED", "STEP_STARTED", "THINKING_CONTENT",
                     "TEXT_MESSAGE_CONTENT", "TOOL_CALL_RESULT", "RUN_FINISHED"):
        assert expected in rehydrated, f"{expected} missing from rehydrated trace"

    # Chat history hydrates too.
    history = client.get(f"/api/sessions/{sid}/history").json()
    roles = [m["role"] for m in history]
    assert "user" in roles and "agent" in roles

    # The replay endpoint reconstructs the persisted data-plane actions and
    # folds workspace state at the cursor — the whole chain (emission ->
    # coalescer -> store -> read-path -> stateAt fold) on real persisted data.
    if has_workspace:
        replay = client.get(f"/api/sessions/{sid}/replay").json()
        assert replay["total"] >= 1, "no replayable vfs_ops persisted"
        assert replay["actions"], "replay returned no actions"
        assert replay["actions"][-1]["tool_call_id"], (
            "persisted vfs_op missing tool_call_id correlation")
        assert replay["state"]["cursor_op"] is not None
        assert "reads_so_far" in replay["state"]

    # The session reappears in the listing, sourced from the store.
    assert any(s["id"] == sid for s in client.get("/api/sessions").json())

    # Derived projection tables were populated by the same turn.
    dsn = os.environ["DATABASE_URL"]
    counts = _wait_for(lambda: (lambda c: c if c["runs"] else None)(
        asyncio.run(_derived_counts(dsn, sid))))
    assert counts is not None
    assert counts["runs"] >= 1
    assert counts["steps"] >= 1
    assert counts["tool_calls"] >= 1
    assert counts["stream"] >= 1
    if live_vfs:
        assert "CUSTOM" in rehydrated
        assert counts["vfs_ops"] >= 1

    # An investigation attached to the session is server-persisted and reloads.
    inv = client.post("/api/investigations", json={
        "sessionId": sid, "title": "IT triage", "trigger": "manual",
        "severity": "P2",
    })
    assert inv.status_code == 200
    assert inv.json()["severity"] == "P2"
    refetched = client.get(f"/api/investigations/{sid}").json()
    assert refetched["title"] == "IT triage"
    assert refetched["status"] == "running"
