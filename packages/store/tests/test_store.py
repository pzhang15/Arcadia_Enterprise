from __future__ import annotations

from arcadia_store.types import (Drained, EventRow, MessageRow, RunRow,
                                 SessionRow, StepRow, StreamEventRow,
                                 ToolCallRow, VfsOpRow)


def _session(sid: str = "sess1") -> SessionRow:
    return SessionRow(id=sid,
                      services=["it"],
                      status="ready",
                      created_at_ms=1000,
                      updated_at_ms=1000,
                      has_workspace=True)


async def test_write_and_get_trace(store):
    events = [
        EventRow("sess1", 1, "RUN_STARTED", {
            "type": "RUN_STARTED",
            "run_id": "r1"
        }, 10),
        EventRow("sess1", 2, "TEXT_MESSAGE_CONTENT", {
            "type": "TEXT_MESSAGE_CONTENT",
            "delta": "hi"
        }, 11),
    ]
    await store.write_batch(Drained(sessions=[_session()], events=events))
    trace = await store.get_trace("sess1")
    assert [e["type"]
            for e in trace] == ["RUN_STARTED", "TEXT_MESSAGE_CONTENT"]
    assert trace[1]["delta"] == "hi"
    assert await store.get_trace("sess1", after_seq=1) == [trace[1]]


async def test_next_seq(store):
    assert await store.next_seq("sess1") == 1
    await store.write_batch(
        Drained(sessions=[_session()],
                events=[EventRow("sess1", 3, "CUSTOM", {"type": "CUSTOM"},
                                 1)]))
    assert await store.next_seq("sess1") == 4


async def test_history_and_list_sessions(store):
    await store.write_batch(
        Drained(sessions=[_session()],
                messages=[
                    MessageRow("sess1", "user", "hello", 2000),
                    MessageRow("sess1", "agent", "world", 3000),
                ]))
    hist = await store.get_history("sess1")
    assert [m["content"] for m in hist] == ["hello", "world"]
    assert hist[0]["timestamp"] == 2.0
    listed = await store.list_sessions()
    assert listed[0]["id"] == "sess1"
    assert listed[0]["message_count"] == 2
    assert listed[0]["last_message"] == "world"
    assert listed[0]["has_workspace"] is True


async def test_run_upsert_collapses(store):
    await store.write_batch(
        Drained(sessions=[_session()],
                runs=[
                    RunRow("r1", "sess1", "running", 10),
                    RunRow("r1", "sess1", "completed", 10, ended_at_ms=20),
                ]))
    # second upsert in same batch wins; no duplicate-key error
    sess = await store.get_session("sess1")
    assert sess["id"] == "sess1"


async def test_stream_events_replay_and_prune(store):
    rows = [
        StreamEventRow(seq=i,
                       type="command",
                       payload={
                           "type": "command",
                           "seq": i
                       },
                       timestamp_ms=i,
                       session="sess1") for i in range(1, 11)
    ]
    await store.write_batch(Drained(stream=rows))
    assert await store.max_stream_seq() == 10
    after = await store.query_stream_events(after_seq=7)
    assert [e["seq"] for e in after] == [8, 9, 10]
    recent = await store.recent_stream_events(limit=3)
    assert [e["seq"] for e in recent] == [8, 9, 10]
    pruned = await store.prune_stream_events(keep_last_n=3)
    assert pruned == 7
    assert await store.query_stream_events(after_seq=0) == recent


async def test_investigations_crud(store):
    created = await store.upsert_investigation({
        "session_id": "sess1",
        "title": "Incident",
        "template_id": "custom",
        "severity": "P2",
        "status": "running",
        "trigger": "alert",
        "authority": "read_only",
        "created_at_ms": 100,
        "updated_at_ms": 100,
    })
    assert created["severity"] == "P2"
    patched = await store.patch_investigation("sess1", {
        "status": "resolved",
        "updated_at_ms": 200
    })
    assert patched["status"] == "resolved"
    assert patched["title"] == "Incident"
    assert await store.patch_investigation("missing", {"status": "x"}) is None
    listed = await store.list_investigations(status="resolved")
    assert len(listed) == 1
    await store.delete_investigation("sess1")
    assert await store.get_investigation("sess1") is None


async def test_console_workspace_roundtrip(store):
    await store.upsert_console_workspace({
        "id":
        "ws1",
        "name":
        "demo",
        "template_id":
        "custom",
        "mode":
        "TEST",
        "branch":
        "main",
        "status":
        "ready",
        "created_at":
        1.0,
        "mount_specs": [{
            "path": "/scratch",
            "mode": "rw"
        }],
        "mounts": [],
        "promoted_keys": ["0:write:/a"],
        "snapshots": [],
        "effects_cache": [{
            "key": "0:write:/a"
        }],
        "overlay_cache":
        None,
        "trajectory_cache":
        None,
    })
    rows = await store.list_console_workspaces()
    assert rows[0]["id"] == "ws1"
    assert rows[0]["promoted_keys"] == ["0:write:/a"]
    assert rows[0]["effects_cache"] == [{"key": "0:write:/a"}]
    await store.delete_console_workspace("ws1")
    assert await store.list_console_workspaces() == []


async def test_scorecards(store):
    card = {"scenario_id": "s", "task_id": "t", "composite": 0.9}
    await store.upsert_scorecard({
        "scenario_id": "s",
        "sweep_id": "sw1",
        "run_id": "run1",
        "task_id": "t",
        "surface": "l1",
        "model": "m",
        "seed": 1,
        "passed_gates": True,
        "composite": 0.9,
        "failure_modes": [],
        "card_json": card,
        "created_at_ms": 1,
    })
    assert await store.list_sweeps() == [{"scenario": "s", "sweep_id": "sw1"}]
    assert await store.get_scorecards("s", "sw1") == [card]
    assert await store.get_scorecard("s", "sw1", "run1") == card
    await store.upsert_sweep_aggregate("s", "sw1", {"n_runs": 1})
    assert await store.get_sweep_aggregate("s", "sw1") == {"n_runs": 1}


async def test_vfs_ops_read_path_round_trip(store):
    await store.write_batch(
        Drained(sessions=[_session()],
                runs=[RunRow("r1", "sess1", "completed", 10, ended_at_ms=50)],
                steps=[
                    StepRow("step-1",
                            "r1",
                            "sess1",
                            "Iteration 1",
                            "completed",
                            11,
                            ended_at_ms=40)
                ],
                tool_calls=[
                    ToolCallRow("tc1",
                                "sess1",
                                "r1",
                                "step-1",
                                "exec",
                                args="cat /s3/a.json",
                                status="completed",
                                started_at_ms=12)
                ],
                vfs_ops=[
                    VfsOpRow("sess1",
                             "read",
                             "/s3/a.json",
                             "s3",
                             38204,
                             210,
                             20,
                             run_id="r1",
                             tool_call_id="tc1",
                             mount_prefix="/s3",
                             fingerprint="etag-9a1f",
                             revision="v3"),
                    VfsOpRow("sess1",
                             "write",
                             "/rca.md",
                             "ram",
                             4280,
                             6,
                             30,
                             run_id="r1",
                             tool_call_id="tc1",
                             mount_prefix="/"),
                ]))
    ops = await store.get_vfs_ops("sess1")
    assert [o["op"] for o in ops] == ["read", "write"]
    assert ops[0]["tool_call_id"] == "tc1"
    assert ops[0]["fingerprint"] == "etag-9a1f"
    assert ops[0]["revision"] == "v3"
    assert ops[1]["path"] == "/rca.md"
    assert [r["run_id"] for r in await store.get_runs("sess1")] == ["r1"]
    assert [s["step_id"] for s in await store.get_steps("sess1", run_id="r1")
            ] == ["step-1"]
    assert [
        t["tool_call_id"]
        for t in await store.get_tool_calls("sess1", run_id="r1")
    ] == ["tc1"]
    assert len(await store.get_vfs_ops("sess1", run_id="r1")) == 2
