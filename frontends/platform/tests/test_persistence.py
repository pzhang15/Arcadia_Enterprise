import time

import server


def _wait_for(predicate, timeout: float = 5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.1)
    return predicate()


def test_session_trace_and_history_survive_restart(client, monkeypatch):
    # Force the deterministic no-key stream path (.env may supply a real key).
    monkeypatch.setattr(server, "OPENAI_API_KEY", "")
    created = client.post("/api/sessions", json={"services": ["it"]})
    assert created.status_code == 200, created.text
    sid = created.json()["id"]

    streamed = client.post(f"/api/sessions/{sid}/message/stream",
                           json={"message": "hello agent"})
    assert streamed.status_code == 200, streamed.text
    assert "RUN_STARTED" in streamed.text

    # Simulate a server restart: drop the in-memory session so reads must
    # hydrate from the persistent store.
    def _evict_and_fetch_trace():
        server._sessions.pop(sid, None)
        resp = client.get(f"/api/sessions/{sid}/trace")
        if resp.status_code != 200:
            return None
        body = resp.json()
        types = [e["type"] for e in body["events"]]
        return body if "RUN_FINISHED" in types else None

    trace = _wait_for(_evict_and_fetch_trace)
    assert trace is not None, "trace did not persist after eviction"
    types = [e["type"] for e in trace["events"]]
    assert "RUN_STARTED" in types
    assert "RUN_FINISHED" in types
    assert "TEXT_MESSAGE_CONTENT" in types

    history = client.get(f"/api/sessions/{sid}/history")
    assert history.status_code == 200, history.text
    roles = [m["role"] for m in history.json()]
    assert "user" in roles and "agent" in roles

    status = client.get(f"/api/sessions/{sid}/status")
    assert status.status_code == 200
    assert status.json()["id"] == sid

    listed = client.get("/api/sessions").json()
    assert any(s["id"] == sid for s in listed)


def test_stream_events_get_monotonic_seq(client):
    seq_before = server._stream_seq
    res = client.post("/ingest",
                      json={"type": "command", "agent": "probe",
                            "session": "persist-test", "command": "ls"})
    assert res.status_code == 200
    assert server._stream_seq > seq_before
    buffered = [e for e in server._event_buffer
                if e.get("session") == "persist-test"]
    assert buffered and buffered[-1]["seq"] > seq_before
