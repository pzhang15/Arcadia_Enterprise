import server


def _read(idx, path, source="s3", fp=None, ts=None):
    return {
        "idx": idx,
        "op": "read",
        "path": path,
        "source": source,
        "bytes": 100,
        "duration_ms": 5,
        "mount_prefix": "/s3",
        "fingerprint": fp,
        "revision": None,
        "is_cache": source == "ram",
        "tool_call_id": "tc1",
        "run_id": "r1",
        "timestamp": ts or idx,
    }


def _write(idx, path, ts=None):
    return {
        "idx": idx,
        "op": "write",
        "path": path,
        "source": "ram",
        "bytes": 4280,
        "duration_ms": 6,
        "mount_prefix": "/",
        "fingerprint": None,
        "revision": None,
        "is_cache": True,
        "tool_call_id": "tc2",
        "run_id": "r1",
        "timestamp": ts or idx,
    }


def test_fold_reads_grow_with_cursor_and_exclude_future():
    actions = [
        _read(0, "/s3/a.json"),
        _read(1, "/s3/b.json"),
        _write(2, "/rca.md")
    ]
    s0 = server._fold_replay_state(actions, 0)
    assert s0["reads_so_far"] == ["/s3/a.json"]
    assert s0["overlay"] == []
    s1 = server._fold_replay_state(actions, 1)
    assert s1["reads_so_far"] == ["/s3/a.json", "/s3/b.json"]
    assert s1["overlay"] == []


def test_fold_write_cursor_diff_and_overlay():
    actions = [_read(0, "/s3/a.json"), _write(1, "/rca.md")]
    s = server._fold_replay_state(actions, 1)
    assert [o["path"] for o in s["overlay"]] == ["/rca.md"]
    assert s["diff"]["kind"] == "write"
    assert s["diff"]["path"] == "/rca.md"
    assert s["diff"]["added_bytes"] == 4280
    assert s["reads_so_far"] == ["/s3/a.json"]


def test_fold_read_cursor_surfaces_fingerprint_and_cache():
    actions = [_read(0, "/s3/a.json", source="ram", fp="etag-9a1f")]
    s = server._fold_replay_state(actions, 0)
    assert s["diff"]["kind"] == "read"
    assert s["diff"]["is_cache"] is True
    assert s["diff"]["fingerprint"] == "etag-9a1f"


def test_replay_endpoint_empty_session(client):
    resp = client.get("/api/sessions/no-such-session/replay")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 0
    assert body["actions"] == []
    assert body["state"]["reads_so_far"] == []
    assert body["state"]["cursor_op"] is None
