def test_investigation_crud(client):
    sid = "inv-sess-1"
    created = client.post("/api/investigations", json={
        "sessionId": sid, "title": "Payment outage", "trigger": "alert",
        "triggerRef": "INC-91204", "severity": "P1",
    })
    assert created.status_code == 200, created.text
    meta = created.json()
    assert meta["sessionId"] == sid
    assert meta["severity"] == "P1"
    assert meta["status"] == "running"  # default
    assert meta["authority"] == "read_only"  # default
    assert meta["triggerRef"] == "INC-91204"
    created_at = meta["createdAt"]
    assert created_at and meta["updatedAt"]

    fetched = client.get(f"/api/investigations/{sid}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Payment outage"

    listed = client.get("/api/investigations").json()
    assert any(m["sessionId"] == sid for m in listed)

    patched = client.patch(f"/api/investigations/{sid}", json={
        "status": "resolved", "resolution": "rolled back deploy",
    })
    assert patched.status_code == 200
    body = patched.json()
    assert body["status"] == "resolved"
    assert body["resolution"] == "rolled back deploy"
    assert body["title"] == "Payment outage"  # preserved
    assert body["createdAt"] == created_at  # preserved
    assert body["updatedAt"] >= created_at

    by_status = client.get("/api/investigations", params={"status": "resolved"}).json()
    assert any(m["sessionId"] == sid for m in by_status)

    assert client.get("/api/investigations/does-not-exist").status_code == 404

    assert client.delete(f"/api/investigations/{sid}").status_code == 200
    assert client.get(f"/api/investigations/{sid}").status_code == 404
