import json
from pathlib import Path


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text())


def test_seed_writes_expected_top_level_dirs(disk_root):
    names = {p.name for p in Path(disk_root).iterdir()}
    assert names == {"slack", "tickets", "github", "pagerduty", "datadog"}


def test_seed_file_count_is_stable(disk_root):
    n = sum(1 for _ in Path(disk_root).rglob("*") if _.is_file())
    assert n == 42, f"expected 42 files, got {n}"


def test_inc_5521_references_ops_1247(disk_root):
    """PagerDuty INC-5521 should be cross-referenced by Jira OPS-1247."""
    pd_inc = _read_json(
        disk_root / "pagerduty/incidents/triggered/INC-5521.json")
    assert pd_inc["service"]["name"] == "payments-api"
    ops_dir = disk_root / "tickets/queues/ops/open"
    ops_1247 = [p for p in ops_dir.iterdir()
                if p.name.startswith("OPS-1247__")]
    assert ops_1247, "OPS-1247 missing from tickets"
    ticket = _read_json(ops_1247[0])
    assert "INC-5521" in ticket.get("linked_incidents", [])


def test_deployment_d4e5f6_references_commit_f3a1b2c8(disk_root):
    """Deployment d4e5f6 sha must match commit f3a1b2c8."""
    deploy = _read_json(
        disk_root / "github/repos/meridian-labs/payments-api"
        "/deployments/d4e5f6.json")
    assert deploy["sha"].startswith("f3a1b2c8")
    commit = _read_json(
        disk_root / "github/repos/meridian-labs/payments-api"
        "/commits/f3a1b2c8.json")
    assert commit["sha"] == deploy["sha"]
    assert "connection pool" in commit["commit"]["message"].lower()


def test_datadog_logs_show_pool_exhaustion_after_deploy(disk_root):
    """Datadog logs should contain connection pool errors after 14:00."""
    logs_path = disk_root / "datadog/logs/payments-api/2026-05-15.jsonl"
    assert logs_path.exists()
    lines = [json.loads(line) for line in logs_path.read_text().splitlines()
             if line.strip()]
    errors = [e for e in lines if e["level"] == "ERROR"]
    assert len(errors) >= 4
    pool_errors = [e for e in errors
                   if "connection pool exhausted" in e["message"]]
    assert pool_errors
    assert all(e["attributes"]["pool_size"] == 10 for e in pool_errors)


def test_datadog_metrics_show_latency_spike(disk_root):
    """P99 latency metric should spike at 14:00."""
    p99 = _read_json(
        disk_root / "datadog/metrics/payments-api/latency_p99.json")
    points = {ts: val for ts, val in p99["points"]}
    assert points["2026-05-15T13:45:00Z"] < 500
    assert points["2026-05-15T14:00:00Z"] > 2000


def test_slack_incidents_channel_discusses_inc_5521(disk_root):
    """The #incidents Slack channel should mention the connection pool."""
    incidents_dir = disk_root / "slack/channels/incidents__C001/2026-05-15"
    assert incidents_dir.exists()
    chat = (incidents_dir / "chat.jsonl").read_text()
    assert "connection pool" in chat.lower()
    assert "d4e5f6" not in chat
    assert "f3a1b2c8" not in chat


def test_resolved_incident_5518_links_to_ops_1243(disk_root):
    """Resolved INC-5518 should have a corresponding resolved OPS-1243."""
    pd_inc = _read_json(
        disk_root / "pagerduty/incidents/resolved/INC-5518.json")
    assert pd_inc["status"] == "resolved"
    ops_dir = disk_root / "tickets/queues/ops/resolved"
    ops_1243 = [p for p in ops_dir.iterdir()
                if p.name.startswith("OPS-1243__")]
    assert ops_1243
    ticket = _read_json(ops_1243[0])
    assert "INC-5518" in ticket.get("linked_incidents", [])
    assert "a1b2c3" in ticket["body"]
