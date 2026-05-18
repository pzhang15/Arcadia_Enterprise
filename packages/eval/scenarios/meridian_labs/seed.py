import json
import shutil
from pathlib import Path

DEFAULT_ROOT = str(
    (Path(__file__).resolve().parent / "fixture" / "disk").resolve())

USERS = [
    {"id": "U001", "handle": "alice.chen", "name": "Alice Chen",
     "email": "alice.chen@meridian-labs.com",
     "title": "Staff Engineer, Platform Lead"},
    {"id": "U002", "handle": "bob.martinez", "name": "Bob Martinez",
     "email": "bob.martinez@meridian-labs.com", "title": "Senior SRE"},
    {"id": "U003", "handle": "carol.kim", "name": "Carol Kim",
     "email": "carol.kim@meridian-labs.com", "title": "Platform Engineer"},
    {"id": "U004", "handle": "dave.thompson", "name": "Dave Thompson",
     "email": "dave.thompson@meridian-labs.com",
     "title": "Engineering Manager, Payments"},
    {"id": "U005", "handle": "eve.nakamura", "name": "Eve Nakamura",
     "email": "eve.nakamura@meridian-labs.com",
     "title": "Senior Backend Engineer"},
    {"id": "U006", "handle": "frank.osei", "name": "Frank Osei",
     "email": "frank.osei@meridian-labs.com", "title": "Backend Engineer"},
    {"id": "U007", "handle": "grace.liu", "name": "Grace Liu",
     "email": "grace.liu@meridian-labs.com", "title": "Tech Lead, Identity"},
    {"id": "U008", "handle": "hassan.ali", "name": "Hassan Ali",
     "email": "hassan.ali@meridian-labs.com", "title": "Senior Engineer"},
    {"id": "U009", "handle": "iris.petrova", "name": "Iris Petrova",
     "email": "iris.petrova@meridian-labs.com", "title": "Frontend Lead"},
    {"id": "U010", "handle": "james.wilson", "name": "James Wilson",
     "email": "james.wilson@meridian-labs.com",
     "title": "Senior Frontend Engineer"},
    {"id": "U011", "handle": "karen.mitchell", "name": "Karen Mitchell",
     "email": "karen.mitchell@meridian-labs.com", "title": "VP Engineering"},
    {"id": "U012", "handle": "maya.krishnan", "name": "Maya Krishnan",
     "email": "maya.krishnan@meridian-labs.com",
     "title": "Head of Customer Success"},
]

CHANNELS = [
    {"id": "C001", "name": "incidents"},
    {"id": "C002", "name": "platform-engineering"},
    {"id": "C003", "name": "payments-eng"},
    {"id": "C004", "name": "deploys"},
    {"id": "C005", "name": "customer-updates"},
    {"id": "C008", "name": "on-call"},
]

CHANNEL_MESSAGES: dict[str, list[tuple[str, str, str, str]]] = {
    "C001": [
        ("2026-05-14", "U007", "1715673000.000100",
         "Root cause identified: commit a1b2c3 changed Redis TTL from "
         "3600 to 60 (seconds). This was a typo. Rolling back now."),
        ("2026-05-14", "U001", "1715674800.000100",
         "Rollback confirmed. Token refresh success rate back to 99.97%. "
         "Scheduling postmortem for Friday."),
        ("2026-05-15", "U002", "1715759000.000100",
         "Acknowledged. Looking at this now. P99 jumped from ~200ms "
         "to 2100ms at exactly 14:00."),
        ("2026-05-15", "U006", "1715759200.000100",
         "Looking now. The commit changed connection pool settings - "
         "reduced connectionPoolSize from 50 to 10 and adjusted timeout."),
        ("2026-05-15", "U002", "1715759400.000100",
         "Confirmed in Datadog: seeing `connection pool exhausted` errors "
         "starting at exactly 14:00:30. 847 occurrences in the last 10 "
         "minutes. This is almost certainly the pool size reduction."),
        ("2026-05-15", "U001", "1715759600.000100",
         "Should we rollback the deployment? I can trigger it from the "
         "CI pipeline."),
        ("2026-05-15", "U002", "1715759800.000100",
         "Yes, let's rollback. The connection pool change is clearly "
         "the cause. @alice.chen please go ahead."),
    ],
    "C004": [
        ("2026-05-14", "U001", "1715702400.000100",
         "Deploy succeeded - auth-service v1.52.1 -> production. "
         "Commit: b2c3d4 by @grace.liu - 'add token rotation metrics'. "
         "Duration: 2m 58s | Status: healthy"),
        ("2026-05-15", "U001", "1715755800.000100",
         "Deploy succeeded - merchant-dashboard v2.41.3 -> production. "
         "Commit: e7f8g9 by @james.wilson - 'fix transaction history "
         "pagination'. Duration: 3m 42s | Status: healthy"),
        ("2026-05-15", "U001", "1715758740.000100",
         "Deploy succeeded - payments-api v3.18.7 -> production. "
         "Commit: f3a1b2c8 by @frank.osei - 'optimize connection pool "
         "settings'. Duration: 4m 15s | Status: healthy"),
    ],
    "C005": [
        ("2026-05-12", "U005", "1715540700.000100",
         "Resolved - Webhook Delivery Delays. Webhook delivery latency "
         "has returned to normal levels. All queued events have been "
         "delivered. Duration: ~2.5 hours. Root cause: Queue congestion "
         "from a high-volume endpoint."),
        ("2026-05-14", "U001", "1715672100.000100",
         "Service Notice - Authentication Service. We identified an issue "
         "affecting token refresh for some API integrations beginning at "
         "approximately 08:30 UTC. Our team has identified the root cause "
         "and is deploying a fix. ETA: 10:00 UTC."),
        ("2026-05-14", "U001", "1715675100.000100",
         "Resolved - Authentication Service. The token refresh issue has "
         "been fully resolved as of 09:50 UTC. Duration: ~80 minutes. "
         "Root cause: Configuration error in a recent deployment "
         "(rolled back)."),
    ],
}

DMS: list[dict] = []
DM_MESSAGES: dict[str, list[tuple[str, str, str, str]]] = {}


def _slack_msg(uid: str, ts: str, text: str) -> dict:
    return {
        "type": "message",
        "user": uid,
        "text": text,
        "ts": ts,
        "team": "T_MERIDIAN",
    }


def write_slack(root: Path) -> None:
    """Materialize Slack channels and user profiles on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    slack_root = root / "slack"
    if slack_root.exists():
        shutil.rmtree(slack_root)
    for ch in CHANNELS:
        ch_dir = slack_root / "channels" / f"{ch['name']}__{ch['id']}"
        days: dict[str, list[dict]] = {}
        for date, uid, ts, text in CHANNEL_MESSAGES.get(ch["id"], []):
            days.setdefault(date, []).append(_slack_msg(uid, ts, text))
        for date, msgs in days.items():
            day_dir = ch_dir / date
            day_dir.mkdir(parents=True, exist_ok=True)
            (day_dir / "files").mkdir(exist_ok=True)
            (day_dir / "chat.jsonl").write_text(
                "\n".join(json.dumps(m, ensure_ascii=False) for m in msgs)
                + "\n")
        if not days:
            ch_dir.mkdir(parents=True, exist_ok=True)
    users_dir = slack_root / "users"
    users_dir.mkdir(parents=True, exist_ok=True)
    for u in USERS:
        profile = {
            "id": u["id"],
            "name": u["handle"],
            "real_name": u["name"],
            "profile": {"title": u["title"], "email": u["email"]},
        }
        (users_dir / f"{u['handle']}__{u['id']}.json").write_text(
            json.dumps(profile, indent=2))


def _user_obj(handle: str) -> dict:
    u = next(u for u in USERS if u["handle"] == handle)
    return {"id": u["id"], "name": u["name"], "email": u["email"]}


def _ticket(tid, subject, body, requester, queue, status, priority,
            created_at, updated_at, assignee=None, tags=None,
            related_tickets=None, comments=None, severity=None,
            linked_incidents=None, resolved=None, resolution=None,
            project=None, labels=None, **extra):
    t = {
        "ticket_id": tid,
        "subject": subject,
        "body": body,
        "requester": requester,
        "assignee": assignee,
        "queue": queue,
        "status": status,
        "priority": priority,
        "created_at": created_at,
        "updated_at": updated_at,
        "tags": tags or [],
        "related_tickets": related_tickets or [],
        "comments": comments or [],
    }
    if severity:
        t["severity"] = severity
    if linked_incidents:
        t["linked_incidents"] = linked_incidents
    if resolved:
        t["resolved"] = resolved
    if resolution:
        t["resolution"] = resolution
    if project:
        t["project"] = project
    if labels:
        t["labels"] = labels
    return t


def _slugify(text: str, max_len: int = 32) -> str:
    out = []
    for ch in text.lower().strip():
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("_")
    slug = "".join(out)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug[:max_len].strip("_") or "ticket"


def write_tickets(root: Path) -> None:
    """Materialize the OPS and PAY ticket queues on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    tickets_root = root / "tickets"
    if tickets_root.exists():
        shutil.rmtree(tickets_root)
    ops_q = tickets_root / "queues" / "ops"
    for s in ("open", "in_progress", "resolved"):
        (ops_q / s).mkdir(parents=True, exist_ok=True)
    pay_q = tickets_root / "queues" / "pay"
    for s in ("open", "in_progress", "resolved"):
        (pay_q / s).mkdir(parents=True, exist_ok=True)
    (tickets_root / "draft").mkdir(parents=True, exist_ok=True)

    open_tickets = [
        _ticket(
            "OPS-1247",
            "P99 latency spike on payments-api exceeding SLA threshold",
            "PagerDuty alert INC-5521 triggered at 14:02 UTC. P99 latency "
            "for /v1/payments/charge endpoint exceeded 2000ms (SLA: 500ms). "
            "Error rate also elevated to 4.2% (baseline: 0.3%). Correlated "
            "with deployment d4e5f6 at 14:00 UTC.",
            {"id": "pagerduty-integration", "name": "PagerDuty", "email": ""},
            "ops", "open", "P1",
            "2026-05-15T14:05:00Z", "2026-05-15T14:05:00Z",
            assignee=_user_obj("bob.martinez"),
            severity="sev1",
            linked_incidents=["INC-5521"],
            tags=["incident", "payments-api", "latency"],
            project="OPS",
        ),
        _ticket(
            "OPS-1245",
            "Intermittent 502 errors on merchant-dashboard API calls",
            "Multiple merchants reported 502 errors when loading transaction "
            "history. Appears to be related to connection pool exhaustion on "
            "the BFF layer. Rate: ~2% of requests affected.",
            _user_obj("maya.krishnan"), "ops", "open", "P2",
            "2026-05-15T10:30:00Z", "2026-05-15T13:45:00Z",
            assignee=_user_obj("iris.petrova"),
            severity="sev2",
            tags=["incident", "merchant-dashboard", "502"],
            project="OPS",
            comments=[
                {"author": "U009", "ts": "2026-05-15T11:15:00Z",
                 "body": "Confirmed connection pool exhaustion on the BFF. "
                 "Increasing pool size from 20 to 50 as a temporary fix."},
                {"author": "U012", "ts": "2026-05-15T12:00:00Z",
                 "body": "Three enterprise merchants (Acme Corp, GlobalTech, "
                 "PayRight) have opened support tickets about this."},
            ],
        ),
    ]
    in_progress_tickets: list[dict] = []
    resolved_tickets = [
        _ticket(
            "OPS-1243",
            "Auth service token refresh failures causing 401 cascade",
            "PagerDuty alert INC-5518. Auth service returning 401 for valid "
            "refresh tokens. Root cause: Redis cache TTL misconfiguration in "
            "commit a1b2c3. Rolled back at 09:45 UTC.",
            {"id": "pagerduty-integration", "name": "PagerDuty", "email": ""},
            "ops", "resolved", "P1",
            "2026-05-14T08:30:00Z", "2026-05-14T10:15:00Z",
            assignee=_user_obj("grace.liu"),
            severity="sev1",
            linked_incidents=["INC-5518"],
            resolved="2026-05-14T09:50:00Z",
            resolution="Rolled back commit a1b2c3. Redis cache TTL restored "
            "to 3600s from 60s (typo in config).",
            tags=["incident", "auth-service", "postmortem-needed"],
            project="OPS",
            comments=[
                {"author": "U007", "ts": "2026-05-14T09:30:00Z",
                 "body": "Root cause identified: commit a1b2c3 changed Redis "
                 "TTL from 3600 to 60 (seconds). Rolling back now."},
                {"author": "U001", "ts": "2026-05-14T10:00:00Z",
                 "body": "Rollback confirmed. Token refresh success rate back "
                 "to 99.97%. Scheduling postmortem for Friday."},
            ],
        ),
        _ticket(
            "OPS-1240",
            "Webhook delivery delays exceeding 30-minute SLA",
            "Webhook queue depth exceeded 50,000. Delivery latency for "
            "payment.completed events averaged 45 minutes vs 30-second SLA. "
            "Root cause: downstream rate limiting from a large merchant.",
            _user_obj("bob.martinez"), "ops", "resolved", "P2",
            "2026-05-12T16:00:00Z", "2026-05-13T09:00:00Z",
            assignee=_user_obj("eve.nakamura"),
            severity="sev2",
            resolved="2026-05-12T18:30:00Z",
            resolution="Implemented per-merchant rate limiting on webhook "
            "delivery. Added circuit breaker for slow endpoints.",
            tags=["incident", "webhook-service", "queue-depth"],
            project="OPS",
        ),
    ]
    pay_done = [
        _ticket(
            "PAY-880", "Upgrade payments-api to Go 1.24", "",
            _user_obj("dave.thompson"), "pay", "resolved", "P4",
            "2026-04-28T10:00:00Z", "2026-05-10T16:00:00Z",
            resolved="2026-05-10T16:00:00Z",
            tags=["tech-debt"], project="PAY",
        ),
    ]
    pay_open = [
        _ticket(
            "PAY-892", "Add support for SEPA instant credit transfers", "",
            _user_obj("frank.osei"), "pay", "open", "P3",
            "2026-05-06T09:00:00Z", "2026-05-06T09:00:00Z",
            tags=["feature", "sepa"], project="PAY",
        ),
        _ticket(
            "PAY-887",
            "Idempotency key collision on high-frequency merchants", "",
            _user_obj("eve.nakamura"), "pay", "open", "P2",
            "2026-05-05T14:00:00Z", "2026-05-05T14:00:00Z",
            tags=["bug", "payments-api", "idempotency"], project="PAY",
        ),
    ]

    def _write(queue_dir, status, tickets):
        for t in tickets:
            fname = f"{t['ticket_id']}__{_slugify(t['subject'])}.json"
            (queue_dir / status / fname).write_text(
                json.dumps(t, indent=2, ensure_ascii=False) + "\n")

    _write(ops_q, "open", open_tickets)
    _write(ops_q, "in_progress", in_progress_tickets)
    _write(ops_q, "resolved", resolved_tickets)
    _write(pay_q, "open", pay_open)
    _write(pay_q, "resolved", pay_done)


def write_github(root: Path) -> None:
    """Materialize GitHub deployments, commits, and PRs on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    gh_root = root / "github"
    if gh_root.exists():
        shutil.rmtree(gh_root)
    repo = gh_root / "repos" / "meridian-labs" / "payments-api"
    for sub in ("deployments", "commits", "pulls"):
        (repo / sub).mkdir(parents=True, exist_ok=True)

    deployments = [
        {
            "id": "d4e5f6",
            "environment": "production",
            "ref": "main",
            "sha": "f3a1b2c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4",
            "description": "Deploy payments-api v3.18.7",
            "creator": {"login": "frank.osei"},
            "created_at": "2026-05-15T13:55:00Z",
            "updated_at": "2026-05-15T13:59:00Z",
            "statuses": [{"state": "success",
                          "created_at": "2026-05-15T13:59:00Z"}],
        },
        {
            "id": "a1b2c3",
            "environment": "production",
            "ref": "main",
            "sha": "7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e",
            "description": "Deploy payments-api v3.18.6",
            "creator": {"login": "eve.nakamura"},
            "created_at": "2026-05-14T10:30:00Z",
            "updated_at": "2026-05-14T10:35:00Z",
            "statuses": [{"state": "success",
                          "created_at": "2026-05-14T10:35:00Z"}],
        },
        {
            "id": "prev001",
            "environment": "production",
            "ref": "main",
            "sha": "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
            "description": "Deploy payments-api v3.18.5",
            "creator": {"login": "dave.thompson"},
            "created_at": "2026-05-13T09:00:00Z",
            "updated_at": "2026-05-13T09:05:00Z",
            "statuses": [{"state": "success",
                          "created_at": "2026-05-13T09:05:00Z"}],
        },
    ]
    for d in deployments:
        (repo / "deployments" / f"{d['id']}.json").write_text(
            json.dumps(d, indent=2))

    critical_commit = {
        "sha": "f3a1b2c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4",
        "commit": {
            "author": {"name": "Frank Osei",
                       "email": "frank.osei@meridian-labs.com",
                       "date": "2026-05-15T13:45:00Z"},
            "message": (
                "optimize connection pool settings\n\n"
                "Reduce connection pool size to improve memory usage "
                "per instance.\nAlso adjusted idle timeout for faster "
                "connection recycling.\n\nRef: PAY-895"),
        },
        "files": [{
            "filename": "config/database.go",
            "status": "modified",
            "additions": 3, "deletions": 3,
            "patch": (
                "@@ -42,9 +42,9 @@ func NewDatabaseConfig() "
                "*DatabaseConfig {\n"
                "     return &DatabaseConfig{\n"
                "-        MaxOpenConns:     50,\n"
                "-        MaxIdleConns:     25,\n"
                "-        ConnMaxIdleTime:  5 * time.Minute,\n"
                "+        MaxOpenConns:     10,\n"
                "+        MaxIdleConns:     5,\n"
                "+        ConnMaxIdleTime:  30 * time.Second,\n"
                "         ConnMaxLifetime:  30 * time.Minute,\n"
                "     }\n"
                " }"),
        }],
        "stats": {"total": 6, "additions": 3, "deletions": 3},
    }
    (repo / "commits" / "f3a1b2c8.json").write_text(
        json.dumps(critical_commit, indent=2))

    pulls = [
        {
            "number": 1847,
            "title": "optimize connection pool settings",
            "user": {"login": "frank.osei"},
            "state": "closed", "merged": True,
            "merged_at": "2026-05-15T13:50:00Z",
            "head": {"ref": "frank/optimize-pool", "sha": "f3a1b2c8"},
            "base": {"ref": "main"},
            "body": "Reduces connection pool to lower memory per pod. "
            "Benchmarked locally with 10 concurrent connections.\n\n"
            "Ref: PAY-895",
            "labels": ["payments-api", "performance"],
        },
        {
            "number": 1845,
            "title": "add SEPA instant credit transfer support",
            "user": {"login": "frank.osei"},
            "state": "open",
            "head": {"ref": "frank/sepa-instant"},
            "base": {"ref": "main"},
            "body": "Implements SEPA Instant Credit Transfer.\n\n"
            "Ref: PAY-892",
            "labels": ["payments-api", "feature", "sepa"],
        },
    ]
    for pr in pulls:
        (repo / "pulls" / f"{pr['number']}.json").write_text(
            json.dumps(pr, indent=2))


def write_pagerduty(root: Path) -> None:
    """Materialize PagerDuty services and incidents on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    pd_root = root / "pagerduty"
    if pd_root.exists():
        shutil.rmtree(pd_root)
    (pd_root / "services").mkdir(parents=True, exist_ok=True)
    for status in ("triggered", "acknowledged", "resolved"):
        (pd_root / "incidents" / status).mkdir(parents=True, exist_ok=True)

    services = [
        {"id": "P001", "name": "payments-api",
         "description": "Core payments processing service",
         "status": "critical",
         "escalation_policy": {"id": "EP001", "name": "Payments On-Call"}},
        {"id": "P002", "name": "auth-service",
         "description": "Authentication and authorization",
         "status": "active",
         "escalation_policy": {"id": "EP002", "name": "Identity On-Call"}},
        {"id": "P003", "name": "merchant-dashboard",
         "description": "Merchant-facing web application",
         "status": "warning",
         "escalation_policy": {"id": "EP003", "name": "Frontend On-Call"}},
        {"id": "P004", "name": "webhook-service",
         "description": "Outbound webhook delivery",
         "status": "active",
         "escalation_policy": {"id": "EP001", "name": "Payments On-Call"}},
    ]
    for svc in services:
        (pd_root / "services" / f"{svc['id']}.json").write_text(
            json.dumps(svc, indent=2))

    triggered = [
        {
            "id": "INC-5521", "incident_number": 5521,
            "title": "P99 latency > 2000ms on payments-api "
            "/v1/payments/charge",
            "status": "triggered", "urgency": "high",
            "severity": {"value": "critical"},
            "service": {"id": "P001", "name": "payments-api"},
            "created_at": "2026-05-15T14:02:00Z",
            "updated_at": "2026-05-15T14:02:00Z",
            "assignments": [
                {"assignee": {"id": "U002", "name": "Bob Martinez",
                              "email": "bob.martinez@meridian-labs.com"}}],
            "acknowledgements": [
                {"at": "2026-05-15T14:03:30Z",
                 "acknowledger": {"id": "U002", "name": "Bob Martinez"}}],
            "body": {
                "type": "incident_body",
                "details": (
                    "Datadog monitor 'payments-api P99 latency' triggered.\n"
                    "Current value: 2147ms\nThreshold: 500ms\n"
                    "Duration: > 2 minutes\n\nTriggered alerts:\n"
                    "- P99 latency on /v1/payments/charge: 2147ms "
                    "(threshold: 500ms)\n"
                    "- Error rate on payments-api: 4.2% (threshold: 1%)"),
            },
        },
    ]
    acknowledged = [
        {
            "id": "INC-5520", "incident_number": 5520,
            "title": "merchant-dashboard 502 error rate > 2%",
            "status": "acknowledged", "urgency": "high",
            "severity": {"value": "warning"},
            "service": {"id": "P003", "name": "merchant-dashboard"},
            "created_at": "2026-05-15T10:28:00Z",
            "assignments": [
                {"assignee": {"id": "U009", "name": "Iris Petrova"}}],
        },
    ]
    resolved = [
        {
            "id": "INC-5518", "incident_number": 5518,
            "title": "Auth service token refresh failure rate > 5%",
            "status": "resolved", "urgency": "high",
            "severity": {"value": "critical"},
            "service": {"id": "P002", "name": "auth-service"},
            "created_at": "2026-05-14T08:28:00Z",
            "resolved_at": "2026-05-14T09:50:00Z",
            "assignments": [
                {"assignee": {"id": "U007", "name": "Grace Liu"}}],
        },
    ]
    for inc in triggered:
        (pd_root / "incidents" / "triggered" / f"{inc['id']}.json"
         ).write_text(json.dumps(inc, indent=2))
    for inc in acknowledged:
        (pd_root / "incidents" / "acknowledged" / f"{inc['id']}.json"
         ).write_text(json.dumps(inc, indent=2))
    for inc in resolved:
        (pd_root / "incidents" / "resolved" / f"{inc['id']}.json"
         ).write_text(json.dumps(inc, indent=2))


def write_datadog(root: Path) -> None:
    """Materialize Datadog logs and metrics on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    dd_root = root / "datadog"
    if dd_root.exists():
        shutil.rmtree(dd_root)
    logs_dir = dd_root / "logs" / "payments-api"
    logs_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir = dd_root / "metrics" / "payments-api"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    log_entries = [
        {"timestamp": "2026-05-15T13:55:00Z", "service": "payments-api",
         "level": "INFO", "message": "payment processed successfully",
         "attributes": {"endpoint": "/v1/payments/charge",
                        "latency_ms": 145}},
        {"timestamp": "2026-05-15T13:58:00Z", "service": "payments-api",
         "level": "INFO",
         "message": "deployment started: v3.18.7 (sha: f3a1b2c8)",
         "attributes": {"version": "v3.18.7", "deployer": "frank.osei"}},
        {"timestamp": "2026-05-15T13:59:00Z", "service": "payments-api",
         "level": "INFO",
         "message": "deployment completed: v3.18.7. Health check passed.",
         "attributes": {"version": "v3.18.7", "duration_seconds": 255}},
        {"timestamp": "2026-05-15T14:00:32Z", "service": "payments-api",
         "level": "ERROR",
         "message": "connection pool exhausted: all 10 connections in use, "
         "23 requests waiting",
         "attributes": {"host": "payments-api-7b4f9d-xk2m1",
                        "pool_size": 10, "waiting": 23}},
        {"timestamp": "2026-05-15T14:00:35Z", "service": "payments-api",
         "level": "ERROR",
         "message": "request timeout after 2000ms on /v1/payments/charge",
         "attributes": {"host": "payments-api-7b4f9d-np8q2",
                        "endpoint": "/v1/payments/charge",
                        "latency_ms": 2000}},
        {"timestamp": "2026-05-15T14:00:38Z", "service": "payments-api",
         "level": "ERROR",
         "message": "connection pool exhausted: all 10 connections in use, "
         "47 requests waiting",
         "attributes": {"host": "payments-api-7b4f9d-np8q2",
                        "pool_size": 10, "waiting": 47}},
        {"timestamp": "2026-05-15T14:00:40Z", "service": "payments-api",
         "level": "ERROR",
         "message": "request timeout after 2000ms on /v1/payments/charge",
         "attributes": {"host": "payments-api-7b4f9d-xk2m1",
                        "endpoint": "/v1/payments/charge",
                        "latency_ms": 2000}},
        {"timestamp": "2026-05-15T14:01:00Z", "service": "payments-api",
         "level": "ERROR",
         "message": "connection pool exhausted: all 10 connections in use, "
         "89 requests waiting",
         "attributes": {"host": "payments-api-7b4f9d-xk2m1",
                        "pool_size": 10, "waiting": 89}},
        {"timestamp": "2026-05-15T14:01:15Z", "service": "payments-api",
         "level": "ERROR",
         "message": "payment processing failed: database connection timeout",
         "attributes": {"host": "payments-api-7b4f9d-np8q2",
                        "error_code": "DB_CONN_TIMEOUT"}},
    ]
    (logs_dir / "2026-05-15.jsonl").write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in log_entries)
        + "\n")

    latency_p99 = {
        "metric": "payments_api.latency.p99",
        "unit": "milliseconds",
        "points": [
            ["2026-05-15T13:00:00Z", 189],
            ["2026-05-15T13:15:00Z", 195],
            ["2026-05-15T13:30:00Z", 192],
            ["2026-05-15T13:45:00Z", 201],
            ["2026-05-15T14:00:00Z", 2147],
            ["2026-05-15T14:15:00Z", 2389],
        ],
        "tags": ["service:payments-api",
                 "endpoint:/v1/payments/charge"],
    }
    error_rate = {
        "metric": "payments_api.error_rate",
        "unit": "percent",
        "points": [
            ["2026-05-15T13:00:00Z", 0.3],
            ["2026-05-15T13:15:00Z", 0.2],
            ["2026-05-15T13:30:00Z", 0.3],
            ["2026-05-15T13:45:00Z", 0.2],
            ["2026-05-15T14:00:00Z", 4.2],
            ["2026-05-15T14:15:00Z", 5.1],
        ],
        "tags": ["service:payments-api"],
    }
    pool_util = {
        "metric": "payments_api.db.pool_utilization",
        "unit": "percent",
        "points": [
            ["2026-05-15T13:00:00Z", 35],
            ["2026-05-15T13:15:00Z", 38],
            ["2026-05-15T13:30:00Z", 36],
            ["2026-05-15T13:45:00Z", 40],
            ["2026-05-15T14:00:00Z", 100],
            ["2026-05-15T14:15:00Z", 100],
        ],
        "tags": ["service:payments-api"],
    }
    (metrics_dir / "latency_p99.json").write_text(
        json.dumps(latency_p99, indent=2))
    (metrics_dir / "error_rate.json").write_text(
        json.dumps(error_rate, indent=2))
    (metrics_dir / "pool_utilization.json").write_text(
        json.dumps(pool_util, indent=2))


def main(root: str | Path = DEFAULT_ROOT, *, clean: bool = True) -> Path:
    """Seed the Meridian Labs SRE corpus on disk.

    Args:
        root (str | Path): Destination directory.
        clean (bool): If True (default), wipe before seeding.
    """
    target = Path(root).expanduser().resolve()
    if clean and target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    write_slack(target)
    write_tickets(target)
    write_github(target)
    write_pagerduty(target)
    write_datadog(target)
    return target
