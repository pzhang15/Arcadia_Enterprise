from __future__ import annotations

from arcadia_store import StreamCoalescer
from arcadia_store.types import FeedOut

LIVE = [
    {
        "type": "RUN_STARTED",
        "timestamp": 1,
        "run_id": "r1",
        "thread_id": "sess1"
    },
    {
        "type": "STEP_STARTED",
        "timestamp": 2,
        "step_id": "s1",
        "step_name": "Iteration 1"
    },
    {
        "type": "THINKING_START",
        "timestamp": 3,
        "thinking_id": "t1",
        "step_id": "s1"
    },
    {
        "type": "THINKING_CONTENT",
        "timestamp": 3,
        "thinking_id": "t1",
        "delta": "Let me "
    },
    {
        "type": "THINKING_CONTENT",
        "timestamp": 3,
        "thinking_id": "t1",
        "delta": "think."
    },
    {
        "type": "THINKING_END",
        "timestamp": 4,
        "thinking_id": "t1"
    },
    {
        "type": "TEXT_MESSAGE_START",
        "timestamp": 5,
        "message_id": "m1",
        "role": "assistant"
    },
    {
        "type": "TEXT_MESSAGE_CONTENT",
        "timestamp": 5,
        "message_id": "m1",
        "delta": "Hello"
    },
    {
        "type": "TEXT_MESSAGE_CONTENT",
        "timestamp": 5,
        "message_id": "m1",
        "delta": " world"
    },
    {
        "type": "TEXT_MESSAGE_END",
        "timestamp": 6,
        "message_id": "m1"
    },
    {
        "type": "TOOL_CALL_START",
        "timestamp": 7,
        "tool_call_id": "tc1",
        "tool_name": "exec"
    },
    {
        "type": "TOOL_CALL_ARGS",
        "timestamp": 7,
        "tool_call_id": "tc1",
        "delta": "ls "
    },
    {
        "type": "TOOL_CALL_ARGS",
        "timestamp": 7,
        "tool_call_id": "tc1",
        "delta": "/tmp"
    },
    {
        "type": "TOOL_CALL_END",
        "timestamp": 8,
        "tool_call_id": "tc1"
    },
    {
        "type": "TOOL_CALL_RESULT",
        "timestamp": 9,
        "tool_call_id": "tc1",
        "result": "files",
        "exit_code": 0
    },
    {
        "type": "CUSTOM",
        "timestamp": 9,
        "name": "vfs_op",
        "value": {
            "op": "read",
            "path": "/tmp/x",
            "bytes": 10,
            "mount_prefix": "/tmp"
        }
    },
    {
        "type": "STEP_FINISHED",
        "timestamp": 10,
        "step_id": "s1"
    },
    {
        "type": "RUN_FINISHED",
        "timestamp": 11,
        "run_id": "r1",
        "thread_id": "sess1"
    },
]


def _replay(events):
    msgs: dict[str, str] = {}
    think: dict[str, str] = {}
    args: dict[str, str] = {}
    for e in events:
        t = e["type"]
        if t == "TEXT_MESSAGE_START":
            msgs.setdefault(e["message_id"], "")
        elif t == "TEXT_MESSAGE_CONTENT":
            msgs[e["message_id"]] = msgs.get(e["message_id"],
                                             "") + (e.get("delta") or "")
        elif t == "THINKING_CONTENT":
            think[e["thinking_id"]] = think.get(e["thinking_id"],
                                                "") + (e.get("delta") or "")
        elif t == "TOOL_CALL_ARGS":
            args[e["tool_call_id"]] = args.get(e["tool_call_id"],
                                               "") + (e.get("delta") or "")
    return {"msgs": msgs, "think": think, "args": args}


def _run_coalescer():
    c = StreamCoalescer("sess1", start_seq=1)
    persisted: list[dict] = []
    agg = FeedOut()
    for ev in LIVE:
        out = c.feed(ev)
        persisted.extend(r.payload for r in out.events)
        agg.runs.extend(out.runs)
        agg.steps.extend(out.steps)
        agg.tool_calls.extend(out.tool_calls)
        agg.vfs_ops.extend(out.vfs_ops)
    fin = c.finalize()
    persisted.extend(r.payload for r in fin.events)
    return persisted, agg, c


def test_replay_equivalence():
    persisted, _agg, _c = _run_coalescer()
    assert _replay(LIVE) == _replay(persisted)
    assert _replay(persisted)["msgs"]["m1"] == "Hello world"
    assert _replay(persisted)["think"]["t1"] == "Let me think."
    assert _replay(persisted)["args"]["tc1"] == "ls /tmp"


def test_coalescing_reduces_event_count():
    persisted, _agg, _c = _run_coalescer()
    # 18 live events collapse: 2 thinking deltas -> 1, 2 text deltas -> 1, 2 arg deltas -> 1
    content_events = [
        e for e in persisted if e["type"] == "TEXT_MESSAGE_CONTENT"
    ]
    assert len(content_events) == 1
    assert content_events[0]["delta"] == "Hello world"
    assert len(persisted) < len(LIVE)


def test_seq_is_contiguous_and_monotonic():
    c = StreamCoalescer("sess1", start_seq=5)
    seqs: list[int] = []
    for ev in LIVE:
        seqs.extend(r.seq for r in c.feed(ev).events)
    seqs.extend(r.seq for r in c.finalize().events)
    assert seqs == list(range(5, 5 + len(seqs)))


def test_derived_rows():
    _persisted, agg, _c = _run_coalescer()
    runs = {r.run_id: r for r in agg.runs}
    steps = {s.step_id: s for s in agg.steps}
    tools = {t.tool_call_id: t for t in agg.tool_calls}
    assert runs["r1"].status == "completed"
    assert steps["s1"].status == "completed"
    assert steps["s1"].reasoning == "Let me think."
    assert steps["s1"].message_id == "m1"
    assert tools["tc1"].status == "completed"
    assert tools["tc1"].args == "ls /tmp"
    assert tools["tc1"].exit_code == 0
    assert len(agg.vfs_ops) == 1
    assert agg.vfs_ops[0].path == "/tmp/x"


def test_vfs_op_carries_correlation_and_fingerprint():
    c = StreamCoalescer("sess1", start_seq=1)
    c.feed({
        "type": "RUN_STARTED",
        "timestamp": 1,
        "run_id": "r1",
        "thread_id": "sess1"
    })
    c.feed({"type": "STEP_STARTED", "timestamp": 2, "step_id": "step-1"})
    c.feed({
        "type": "TOOL_CALL_START",
        "timestamp": 3,
        "tool_call_id": "tc-aa31",
        "tool_name": "exec"
    })
    out = c.feed({
        "type": "CUSTOM",
        "timestamp": 4,
        "name": "vfs_op",
        "value": {
            "op": "read",
            "path": "/s3/dashboards/checkout.json",
            "bytes": 38204,
            "mount_prefix": "/s3",
            "source": "s3",
            "duration_ms": 210,
            "fingerprint": "etag-9a1f",
            "revision": "v3",
            "is_cache": False,
            "tool_call_id": "tc-aa31",
            "step_id": "step-1",
            "run_id": "r1"
        }
    })
    assert len(out.vfs_ops) == 1
    row = out.vfs_ops[0]
    assert row.tool_call_id == "tc-aa31"
    assert row.run_id == "r1"
    assert row.source == "s3"
    assert row.duration_ms == 210
    assert row.fingerprint == "etag-9a1f"
    assert row.revision == "v3"
    assert row.path == "/s3/dashboards/checkout.json"
