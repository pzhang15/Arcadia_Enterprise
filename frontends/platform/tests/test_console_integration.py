import server

DEFAULT_MOUNTS = [
    {"path": "/pagerduty", "mode": "ro"},
    {"path": "/scratch", "mode": "rw"},
]


def _find_mount(detail: dict, prefix_head: str) -> dict:
    for m in detail["mounts"]:
        if m["prefix"].strip("/").split("/")[0] == prefix_head:
            return m
    raise AssertionError(f"mount {prefix_head} not in {detail['mounts']}")


# ── Workspace lifecycle + teardown ──────────────────────────────────────


def test_create_get_list_and_teardown(client, make_ws):
    ws_id = make_ws(name="lifecycle")
    detail = client.get(f"/api/console/workspaces/{ws_id}").json()
    assert detail["id"] == ws_id
    assert detail["status"] == "created"
    assert detail["mode"] == "TEST"

    listing = client.get("/api/console/workspaces").json()
    assert any(w["id"] == ws_id for w in listing)

    deleted = client.delete(f"/api/console/workspaces/{ws_id}")
    assert deleted.status_code == 200
    assert deleted.json()["id"] == ws_id

    gone = client.get(f"/api/console/workspaces/{ws_id}")
    assert gone.status_code == 404
    listing_after = client.get("/api/console/workspaces").json()
    assert not any(w["id"] == ws_id for w in listing_after)


def test_delete_unknown_workspace_404(client):
    assert client.delete("/api/console/workspaces/does-not-exist").status_code == 404


# ── Workspace permissions / effect-class config ─────────────────────────


def test_effect_class_config_from_mounts(client, make_ws):
    ws_id = make_ws(
        mounts=[
            {"path": "/slack", "mode": "ro"},
            {"path": "/finance", "mode": "ro"},
            {"path": "/scratch", "mode": "rw"},
        ],
    )
    detail = client.get(f"/api/console/workspaces/{ws_id}").json()
    assert _find_mount(detail, "slack")["effect_class"] == "external-effect"
    assert _find_mount(detail, "finance")["effect_class"] == "system-of-record"
    assert _find_mount(detail, "scratch")["effect_class"] == "scratch"


def test_mode_test_to_live_and_back(client, make_ws):
    ws_id = make_ws(standup=True)
    live = client.post(f"/api/console/workspaces/{ws_id}/mode", json={"mode": "LIVE"})
    assert live.status_code == 200
    assert live.json()["mode"] == "LIVE"

    test = client.post(f"/api/console/workspaces/{ws_id}/mode", json={"mode": "TEST"})
    assert test.json()["mode"] == "TEST"

    bad = client.post(f"/api/console/workspaces/{ws_id}/mode", json={"mode": "WAT"})
    assert bad.status_code == 400


# ── Stand-up: dry-run + backing pin ─────────────────────────────────────


def test_standup_dryrun_reports_real_backends(client, make_ws):
    ws_id = make_ws(mounts=DEFAULT_MOUNTS)
    dry = client.post(f"/api/console/workspaces/{ws_id}/standup/dryrun").json()
    by_path = {m["path"]: m for m in dry["mounts"]}
    assert by_path["/pagerduty"]["exists"] is True
    assert by_path["/pagerduty"]["files"] > 0
    assert by_path["/scratch"]["exists"] is False
    assert dry["estimated_snapshot_bytes"] >= by_path["/pagerduty"]["bytes"]


def test_standup_pins_backing_and_is_ready(client, make_ws):
    ws_id = make_ws(mounts=DEFAULT_MOUNTS)
    detail = client.post(f"/api/console/workspaces/{ws_id}/standup").json()
    assert detail["status"] == "ready"
    assert detail["pinned_backing"] is True
    prefixes = {m["prefix"].rstrip("/") for m in detail["mounts"]}
    assert "/pagerduty" in prefixes
    assert "/scratch" in prefixes


def test_run_requires_standup(client, make_ws):
    ws_id = make_ws()
    res = client.post(f"/api/console/workspaces/{ws_id}/test-run", json={})
    assert res.status_code == 400


# ── Dispatch the testing agent + permission enforcement ─────────────────


def test_testing_agent_smoke_and_permission_enforcement(client, make_ws):
    ws_id = make_ws(mounts=DEFAULT_MOUNTS, standup=True)
    result = client.post(f"/api/console/workspaces/{ws_id}/test-run", json={}).json()

    assert result["ok"] is True
    assert result["captured_writes"] >= 1

    perms = {p["prefix"].rstrip("/"): p for p in result["permissions"]}
    assert perms["/pagerduty"]["mode"] == "read"
    assert perms["/pagerduty"]["writable"] is False
    assert perms["/pagerduty"]["enforced"] is True
    assert perms["/scratch"]["mode"] == "write"
    assert perms["/scratch"]["writable"] is True
    assert perms["/scratch"]["enforced"] is True

    assert any(s["command"] == "ls -la /" and s["ok"] for s in result["steps"])


def test_testing_agent_custom_commands(client, make_ws):
    ws_id = make_ws(mounts=[{"path": "/scratch", "mode": "rw"}], standup=True)
    result = client.post(
        f"/api/console/workspaces/{ws_id}/test-run",
        json={"commands": ['echo "hello console" > /scratch/note.txt', "cat /scratch/note.txt"]},
    ).json()
    assert result["ok"] is True
    assert result["steps"][0]["wrote"] is True
    assert "hello console" in result["steps"][1]["stdout"]


def test_testing_agent_rejects_bad_commands_payload(client, make_ws):
    ws_id = make_ws(standup=True)
    res = client.post(
        f"/api/console/workspaces/{ws_id}/test-run",
        json={"commands": "not-a-list"},
    )
    assert res.status_code == 400


# ── SSE traces ──────────────────────────────────────────────────────────


def test_events_endpoint_is_registered_as_a_stream(client):
    paths = {getattr(r, "path", None) for r in client.app.routes}
    assert "/events" in paths
    assert "/ingest" in paths


def test_sse_traces_emitted_for_workspace_activity(client, make_ws):
    ws_id = make_ws(mounts=DEFAULT_MOUNTS, standup=True)
    before_len = len(server._event_buffer)
    assert (
        client.post(f"/api/console/workspaces/{ws_id}/test-run", json={}).status_code
        == 200
    )

    new_events = list(server._event_buffer)[before_len:]
    types = {e.get("type") for e in new_events}
    assert "command" in types
    assert "op" in types
    assert "console_test_run" in types
    assert any(
        e.get("path", "").endswith(".mirage_test_probe")
        for e in new_events
        if e.get("type") == "op"
    )
    for evt in new_events:
        assert evt.get("workspace_id") == ws_id or evt.get("session") == ws_id


# ── Overlay / effects / trajectory derivation ───────────────────────────


def test_overlay_and_effects_after_testing_agent(client, make_ws):
    ws_id = make_ws(mounts=[{"path": "/scratch", "mode": "rw"}], standup=True)
    client.post(f"/api/console/workspaces/{ws_id}/test-run", json={})

    overlay = client.get(f"/api/console/workspaces/{ws_id}/overlay").json()
    scratch = next(m for m in overlay["mounts"] if m["prefix"].rstrip("/") == "/scratch")
    assert len(scratch["changes"]) >= 1

    effects = client.get(f"/api/console/workspaces/{ws_id}/effects").json()["effects"]
    assert any(e["path"].endswith(".mirage_test_probe") for e in effects)
    assert all(e["capture_state"] in ("captured", "simulated") for e in effects)


def test_trajectory_unifies_reads_and_writes(client, make_ws):
    ws_id = make_ws(mounts=DEFAULT_MOUNTS, standup=True)
    client.post(f"/api/console/workspaces/{ws_id}/test-run", json={})
    entries = client.get(f"/api/console/workspaces/{ws_id}/trajectory").json()["entries"]
    kinds = {e["kind"] for e in entries}
    assert "read" in kinds
    assert "write" in kinds
    writes = [e for e in entries if e["kind"] == "write"]
    assert all(w["capture_state"] in ("captured", "simulated", "live") for w in writes)


# ── Promote (simulated) ─────────────────────────────────────────────────


def test_promote_marks_effect_live_and_clears_pending(client, make_ws):
    ws_id = make_ws(mounts=[{"path": "/scratch", "mode": "rw"}], standup=True)
    client.post(f"/api/console/workspaces/{ws_id}/test-run", json={})

    effects = client.get(f"/api/console/workspaces/{ws_id}/effects").json()["effects"]
    target = next(e for e in effects if e["path"].endswith(".mirage_test_probe"))
    assert target["promoted"] is False

    promo = client.post(
        f"/api/console/workspaces/{ws_id}/promote",
        json={"keys": [target["key"]]},
    ).json()
    assert promo["simulated"] is True
    assert promo["results"][0]["status"] == "promoted"

    effects_after = client.get(f"/api/console/workspaces/{ws_id}/effects").json()["effects"]
    promoted = next(e for e in effects_after if e["key"] == target["key"])
    assert promoted["promoted"] is True
    assert promoted["capture_state"] == "live"

    detail = client.get(f"/api/console/workspaces/{ws_id}").json()
    assert detail["pending_effects"] == 0


# ── Branch / snapshot / reset ───────────────────────────────────────────


def test_branch_forks_with_parent_link(client, make_ws):
    ws_id = make_ws(standup=True)
    branch = client.post(
        f"/api/console/workspaces/{ws_id}/branch",
        json={"branch": "variant-a"},
    ).json()
    assert branch["parent_id"] == ws_id
    assert branch["branch"] == "variant-a"
    assert branch["status"] == "ready"
    client.delete(f"/api/console/workspaces/{branch['id']}")


def test_snapshot_writes_a_tar(client, make_ws):
    ws_id = make_ws(standup=True)
    snap = client.post(
        f"/api/console/workspaces/{ws_id}/snapshot",
        json={"name": "pristine"},
    ).json()
    assert snap["name"] == "pristine"
    assert snap["size"] > 0


def test_reset_discards_overlay(client, make_ws):
    ws_id = make_ws(mounts=[{"path": "/scratch", "mode": "rw"}], standup=True)
    client.post(f"/api/console/workspaces/{ws_id}/test-run", json={})
    before = client.get(f"/api/console/workspaces/{ws_id}/effects").json()["effects"]
    assert len(before) >= 1

    reset = client.post(f"/api/console/workspaces/{ws_id}/reset").json()
    assert reset["status"] == "ready"

    after = client.get(f"/api/console/workspaces/{ws_id}/effects").json()["effects"]
    assert after == []
    detail = client.get(f"/api/console/workspaces/{ws_id}").json()
    assert detail["pending_effects"] == 0
