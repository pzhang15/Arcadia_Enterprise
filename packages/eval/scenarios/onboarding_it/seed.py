import argparse
import json
import shutil
from pathlib import Path

DEFAULT_ROOT = str(
    (Path(__file__).resolve().parent / "fixture" / "disk").resolve())

USERS = [
    {
        "id": "U101",
        "handle": "alex",
        "name": "Alex Rivera",
        "email": "alex.rivera@northhill.com",
        "title": "Software Engineer"
    },
    {
        "id": "U102",
        "handle": "diana",
        "name": "Diana Park",
        "email": "diana.park@northhill.com",
        "title": "HR Partner"
    },
    {
        "id": "U103",
        "handle": "sam",
        "name": "Sam Chen",
        "email": "sam.chen@northhill.com",
        "title": "IT Lead"
    },
    {
        "id": "U104",
        "handle": "priya",
        "name": "Priya Patel",
        "email": "priya.patel@northhill.com",
        "title": "IT Support Agent"
    },
    {
        "id": "U105",
        "handle": "marcus",
        "name": "Marcus Johnson",
        "email": "marcus.johnson@northhill.com",
        "title": "Eng Lead, Platform"
    },
    {
        "id": "U106",
        "handle": "jordan",
        "name": "Jordan Kim",
        "email": "jordan.kim@northhill.com",
        "title": "Software Engineer"
    },
    {
        "id": "U107",
        "handle": "bob",
        "name": "Bob Lee",
        "email": "bob.lee@northhill.com",
        "title": "Software Engineer"
    },
]

CHANNELS = [
    {
        "id": "C301",
        "name": "it-helpdesk"
    },
    {
        "id": "C302",
        "name": "onboarding"
    },
    {
        "id": "C303",
        "name": "platform-team"
    },
    {
        "id": "C304",
        "name": "general"
    },
    {
        "id": "C305",
        "name": "incidents"
    },
]

DMS = [
    {
        "id": "D201",
        "with_handle": "diana"
    },
    {
        "id": "D202",
        "with_handle": "sam"
    },
    {
        "id": "D203",
        "with_handle": "marcus"
    },
]

CHANNEL_MESSAGES: dict[str, list[tuple[str, str, str, str]]] = {
    "C301": [
        ("2026-05-11", "U104", "1715456400.000100",
         "morning all - I'm picking up the new-hire provisioning queue today."
         ),
        ("2026-05-11", "U101", "1715459000.000100",
         "hi team! my laptop hasn't shown up yet (started today, INC-1001 filed). "
         "tracking number says it's still in transit. anything I can do from "
         "my personal machine in the meantime?"),
        ("2026-05-11", "U103", "1715460000.000100",
         "@alex hang tight - we have a loaner program. priya will hand one off "
         "by EOD. I'll bump INC-1001 priority."),
        ("2026-05-12", "U104", "1715542800.000100",
         "@alex loaner MBP ready for pickup at the IT desk anytime today. "
         "your real machine (Asset MBP-2026-014) is now showing 'out for "
         "delivery' - should land tomorrow."),
        ("2026-05-12", "U101", "1715543700.000100",
         "thanks priya - picking up now. also filed INC-1002 for AWS access "
         "and INC-1004 for the github org invite. let me know if I should "
         "have batched those."),
        ("2026-05-12", "U103", "1715544600.000100",
         "separate tickets are fine. INC-1003 (okta SSO) is in_progress, "
         "should land in the next hour. the access matrix says platform "
         "engineers also need the northhill-platform github org - INC-1004 "
         "covers that."),
    ],
    "C302": [
        ("2026-05-12", "U102", "1715520000.000100",
         "Welcome to NorthHill, @alex! Your buddy this week is @jordan, your "
         "manager is @marcus. The Day-1 checklist lives in the Onboarding "
         "Playbook (gdocs). Ping me if anything is blocked."),
        ("2026-05-12", "U106", "1715521800.000100",
         "@alex glad to have you - I'm your week-1 buddy. dm me anytime. "
         "first thing tomorrow let's pair on getting the platform repo "
         "running locally."),
        ("2026-05-12", "U101", "1715523600.000100",
         "thanks both! laptop is en route (loaner today), tickets filed for "
         "AWS + GitHub. will start on the platform setup with jordan tomorrow."
         ),
    ],
    "C303": [
        ("2026-05-08", "U105", "1715184000.000100",
         "team - alex starts monday on platform. please give them a warm "
         "welcome and set aside time for code-walkthroughs week-1. I'll "
         "share the welcome doc."),
        ("2026-05-12", "U105", "1715528000.000100",
         "@alex welcome aboard. team welcome doc: see /gdocs/owned/. "
         "@jordan owns buddy-week. let's keep the first PR small."),
    ],
    "C304": [
        ("2026-05-12", "U102", "1715518000.000100",
         "Welcoming @alex to the platform team this morning! Day 1 vibes."),
    ],
    "C305": [
        ("2026-04-22", "U103", "1714000000.000100",
         "incident: slack workspace auth provider (okta) is down - reports "
         "of users unable to sign in since 09:14 PT. opening bridge."),
        ("2026-04-22", "U104", "1714003600.000100",
         "two new hires (apr-22 start dates) blocked on day-1 onboarding "
         "because they can't get into slack. provisioning tickets queued "
         "but un-actionable until SSO is back."),
        ("2026-04-22", "U103", "1714010800.000100",
         "okta has restored. backfilling provisioning now. postmortem "
         "writeup tomorrow."),
        ("2026-04-23", "U103", "1714086400.000100",
         "postmortem for the 2026-04-22 outage is up in /gdocs/owned/. "
         "TL;DR: okta IdP cert rotation misconfigured; affected ~40min of "
         "morning auth + 2 new-hire onboardings."),
    ],
}

DM_MESSAGES: dict[str, list[tuple[str, str, str, str]]] = {
    "D201": [
        ("2026-05-11", "U102", "1715454000.000100",
         "Hi Alex - confirming your start date is tomorrow (Mon May 12). "
         "Everything provisioning-wise should be ready by EOD. Loop me in "
         "if anything is missing."),
        ("2026-05-11", "U101", "1715455000.000100",
         "Thanks Diana! Quick question - my laptop hasn't arrived yet, "
         "should I be worried?"),
        ("2026-05-12", "U102", "1715520500.000100",
         "Sam confirmed loaner is ready - go grab it at the IT desk. "
         "Real machine should land Wed. Day-1 checklist is in the "
         "Onboarding Playbook (gdocs)."),
        ("2026-05-12", "U101", "1715524500.000100",
         "Got the loaner, thanks. Working through the playbook now."),
    ],
    "D202": [
        ("2026-05-12", "U101", "1715543000.000100",
         "Hi Sam - filed INC-1002 (AWS) and INC-1004 (GitHub). INC-1003 "
         "(Okta) was already in flight. Status update on those would help "
         "me sequence the rest of day 1."),
        ("2026-05-12", "U103", "1715543900.000100",
         "INC-1003 should resolve within the hour - that unblocks AWS + "
         "GitHub since both gate on SSO. Priya is picking up INC-1002 "
         "after lunch."),
        ("2026-05-12", "U101", "1715544800.000100",
         "Got it. I noticed INC-1006 looks like a near-duplicate of INC-1002 - "
         "should I close it?"),
        ("2026-05-12", "U103", "1715545500.000100",
         "Yes - closing INC-1006 is correct. Priya will fold any context "
         "into INC-1002. Good catch."),
    ],
    "D203": [
        ("2026-05-08", "U105", "1715185000.000100",
         "Hey - excited to have you join Monday. Sharing the Platform "
         "Team Welcome doc (gdocs/owned). Read at your leisure - we'll "
         "cover live in your first 1:1 next week."),
        ("2026-05-12", "U101", "1715526000.000100",
         "Thanks Marcus! Loaner laptop in hand, working through "
         "onboarding tickets. First 1:1 confirmed for Thursday."),
    ],
}


def _slack_msg(uid: str, ts: str, text: str) -> dict:
    return {
        "type": "message",
        "user": uid,
        "text": text,
        "ts": ts,
        "team": "T_NORTHHILL",
    }


def write_slack(root: Path) -> None:
    """Materialize Slack channels, DMs, and user profiles on disk.

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
            (day_dir / "chat.jsonl").write_text("\n".join(
                json.dumps(m, ensure_ascii=False) for m in msgs) + "\n")
        if not days:
            ch_dir.mkdir(parents=True, exist_ok=True)
    for dm in DMS:
        peer = next(u for u in USERS if u["handle"] == dm["with_handle"])
        dm_dir = (slack_root / "dms" / f"{peer['handle']}__{dm['id']}")
        days = {}
        for date, uid, ts, text in DM_MESSAGES.get(dm["id"], []):
            days.setdefault(date, []).append(_slack_msg(uid, ts, text))
        for date, msgs in days.items():
            day_dir = dm_dir / date
            day_dir.mkdir(parents=True, exist_ok=True)
            (day_dir / "files").mkdir(exist_ok=True)
            (day_dir / "chat.jsonl").write_text("\n".join(
                json.dumps(m, ensure_ascii=False) for m in msgs) + "\n")
    users_dir = slack_root / "users"
    users_dir.mkdir(parents=True, exist_ok=True)
    for u in USERS:
        profile = {
            "id": u["id"],
            "name": u["handle"],
            "real_name": u["name"],
            "profile": {
                "title": u["title"],
                "email": u["email"]
            },
        }
        (users_dir / f"{u['handle']}__{u['id']}.json").write_text(
            json.dumps(profile, indent=2))


def _cell(value: object) -> dict:
    s = str(value)
    return {
        "formattedValue": s,
        "userEnteredValue": {
            "stringValue": s
        },
        "effectiveValue": {
            "stringValue": s
        },
    }


def _row(values: list) -> dict:
    return {"values": [_cell(v) for v in values]}


def _gsheet(sid: str, title: str, sheets: list[dict]) -> dict:
    return {
        "spreadsheetId": sid,
        "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{sid}",
        "properties": {
            "title": title,
            "locale": "en_US",
            "timeZone": "America/Los_Angeles",
        },
        "sheets": sheets,
    }


def _tab(sheet_id: int, title: str, rows: list[list]) -> dict:
    return {
        "properties": {
            "sheetId": sheet_id,
            "title": title,
            "index": sheet_id,
            "gridProperties": {
                "rowCount": max(len(rows), 100),
                "columnCount": 26,
            },
        },
        "data": [{
            "rowData": [_row(r) for r in rows]
        }],
    }


NEW_HIRE_TRACKER_ROWS = [
    [
        "Name", "Start Date", "Team", "Manager", "Buddy", "Equipment Status",
        "Access Status", "Day 1 Complete"
    ],
    [
        "Alex Rivera", "2026-05-12", "Platform", "Marcus Johnson",
        "Jordan Kim", "loaner_in_use_pending_shipment", "in_progress", "N"
    ],
    [
        "Priya Wong", "2026-04-22", "IT", "Sam Chen", "Priya Patel",
        "received", "complete", "Y"
    ],
    [
        "Marcus Davis", "2026-04-22", "Platform", "Marcus Johnson",
        "Jordan Kim", "received", "complete", "Y"
    ],
    [
        "Lin Wei", "2026-05-19", "Platform", "Marcus Johnson", "Jordan Kim",
        "ordered", "not_started", "N"
    ],
]

EQUIPMENT_INVENTORY_ROWS = [
    [
        "Asset ID", "Type", "Model", "Serial", "Assigned To", "Location",
        "Status"
    ],
    [
        "MBP-2026-014", "Laptop", "MacBook Pro M4 14\"", "C02XX1Z2J1WL",
        "Alex Rivera", "shipping", "in-shipping"
    ],
    [
        "MBP-2026-LOAN-007", "Laptop (Loaner)", "MacBook Pro M3 14\"",
        "C02LO0AN3WL", "Alex Rivera", "office-sf", "assigned_loaner"
    ],
    [
        "MBP-2026-009", "Laptop", "MacBook Pro M4 14\"", "C02XX1Z2J1WK",
        "Bob Lee", "office-sf", "assigned"
    ],
    [
        "MBP-2026-011", "Laptop", "MacBook Pro M4 14\"", "C02XX1Z2J1WJ",
        "Priya Wong", "office-sf", "assigned"
    ],
    [
        "DELL-MON-022", "Monitor", "Dell U2723QE", "MON022", "", "office-sf",
        "in-stock"
    ],
    [
        "MBP-2026-022", "Laptop", "MacBook Pro M4 14\"", "C02FUTURE0JE",
        "Lin Wei", "warehouse", "ordered"
    ],
]

ACCESS_MATRIX_ROWS = [
    [
        "Role", "Team", "GitHub Org", "Slack Channels", "AWS Account",
        "Postgres DB", "Notion", "Linear Team"
    ],
    [
        "Software Engineer", "Platform", "northhill-platform",
        "platform-team,eng,general", "northhill-platform-prod", "platform_db",
        "Engineering", "Platform"
    ],
    [
        "Software Engineer", "IT", "northhill-it", "it-helpdesk,eng,general",
        "northhill-it-prod", "ops_db", "IT", "IT"
    ],
    [
        "IT Lead", "IT", "northhill-it,northhill-org-admin",
        "it-helpdesk,eng,general,leadership", "northhill-it-prod,northhill-billing",
        "ops_db,billing_db", "IT,Leadership", "IT"
    ],
    [
        "HR Partner", "People", "(none)", "onboarding,general,people-ops",
        "(none)", "(none)", "People,All-hands", "People"
    ],
]


def write_sheets(root: Path) -> None:
    """Materialize the three GSheet JSONs on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    sheets_root = root / "sheets"
    if sheets_root.exists():
        shutil.rmtree(sheets_root)
    owned = sheets_root / "owned"
    shared = sheets_root / "shared"
    owned.mkdir(parents=True, exist_ok=True)
    shared.mkdir(parents=True, exist_ok=True)
    tracker = _gsheet("SH101", "New Hire Tracker",
                      [_tab(0, "Active", NEW_HIRE_TRACKER_ROWS)])
    inventory = _gsheet("SH102", "IT Equipment Inventory",
                        [_tab(0, "Inventory", EQUIPMENT_INVENTORY_ROWS)])
    access = _gsheet("SH103", "Access Matrix",
                     [_tab(0, "By Role", ACCESS_MATRIX_ROWS)])
    (owned / "2026-05-12_New_Hire_Tracker__SH101.gsheet.json").write_text(
        json.dumps(tracker, indent=2))
    (owned /
     "2026-05-12_IT_Equipment_Inventory__SH102.gsheet.json").write_text(
         json.dumps(inventory, indent=2))
    (owned / "2026-05-12_Access_Matrix__SH103.gsheet.json").write_text(
        json.dumps(access, indent=2))


def _gdoc(did: str, title: str, paragraphs: list[str]) -> dict:
    content = []
    for p in paragraphs:
        content.append({
            "paragraph": {
                "elements": [{
                    "textRun": {
                        "content": p + "\n",
                        "textStyle": {}
                    }
                }],
                "paragraphStyle": {},
            }
        })
    return {
        "documentId": did,
        "title": title,
        "body": {
            "content": content
        },
        "documentStyle": {},
        "namedStyles": {},
        "revisionId": "rev-1",
        "suggestionsViewMode": "DEFAULT_FOR_CURRENT_ACCESS",
    }


def write_docs(root: Path) -> None:
    """Materialize the five GDoc JSONs on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    docs_root = root / "gdocs"
    if docs_root.exists():
        shutil.rmtree(docs_root)
    owned = docs_root / "owned"
    shared = docs_root / "shared"
    owned.mkdir(parents=True, exist_ok=True)
    shared.mkdir(parents=True, exist_ok=True)

    playbook = _gdoc("GD101", "Onboarding Playbook", [
        "# NorthHill Onboarding Playbook",
        "Owner: Diana Park (HR). Last updated: 2026-05-10.",
        "## Day 1",
        "- Pick up laptop from IT desk (or arrange loaner if not yet shipped).",
        "- Sign into Okta (SSO triggers auto-provisioning of dependent apps).",
        "- File any missing-access tickets via /tickets/queues/it-helpdesk/.",
        "- Read team welcome doc (manager shares).",
        "- Confirm buddy + first 1:1 with manager.",
        "## Day 2-5",
        "- Complete security training (assigned via email).",
        "- Pair with buddy on dev environment setup.",
        "- Attend new-hire orientation (Wed 10am).",
        "## Week 2",
        "- First 1:1 with manager (themes: scope, growth, expectations).",
        "- Ship a small first PR (buddy reviews).",
    ])

    runbook = _gdoc("GD102", "IT Runbook - New Hire Provisioning", [
        "# IT Runbook: New Hire Provisioning",
        "Owner: Sam Chen (IT Lead). Audience: IT support agents.",
        "## SLA matrix (also see IT_SLA_Matrix doc)",
        "- P1 (blocker, e.g. SSO down for whole org): respond <15min, "
        "resolve <2h, escalate to IT Lead immediately.",
        "- P2 (single-user blocker, e.g. new-hire SSO not working): "
        "respond <2h, resolve <8h.",
        "- P3 (single-user non-blocker, e.g. AWS access for dev): "
        "respond <8h, resolve <48h. Escalate to IT Lead if open >48h.",
        "- P4 (cosmetic / preference): best-effort, target <1wk.",
        "## Provisioning checklist (per role)",
        "- Look up the role row in Access Matrix (sheet SH103).",
        "- For each access listed: file a separate ticket (one per system).",
        "  Reuse existing tickets if a near-duplicate is open.",
        "- For GitHub access: invite to org listed in Access Matrix; "
        "send email confirmation; close ticket only after acceptance.",
        "- For AWS access: provision IAM role per role row; tag with "
        "team + start date; verify SSO works.",
        "- For Slack workspace access: ensure Okta SSO group includes "
        "the user; do NOT manually add (Okta handles it).",
        "## Equipment workflow",
        "- If laptop has not arrived by Day 1: assign loaner from "
        "MBP-LOAN-* pool. Update Equipment Inventory (sheet SH102).",
        "- Real device, on arrival: swap, return loaner.",
    ])

    welcome = _gdoc("GD103", "Platform Team Welcome", [
        "# Welcome to the Platform Team",
        "Author: Marcus Johnson (Eng Lead). Audience: new platform hires.",
        "## Who we are",
        "Platform owns the multi-tenant data plane that NorthHill ships to "
        "customers. We're a team of 9 engineers + 1 EM + 1 PM.",
        "## How we work",
        "- Two-week sprints; planning Mondays, demo Fridays.",
        "- Code reviews within 24h SLA. Merge on green.",
        "- Postmortems are blameless and shared in /gdocs/owned/.",
        "## Your first week",
        "- Pair with your buddy (Jordan Kim) on dev setup.",
        "- Shadow on-call without paging burden (Bob Lee is primary).",
        "- First 1:1 with me (Marcus): pick a Thursday slot.",
    ])

    sla = _gdoc("GD104", "IT SLA Matrix", [
        "# NorthHill IT SLA Matrix",
        "Last updated: 2026-05-08. Owner: Sam Chen.",
        "## Severity definitions",
        "- P1: full org outage, security incident, or VIP blocker. "
        "Page IT Lead immediately.",
        "- P2: single user fully blocked from work (e.g. SSO inaccessible, "
        "no laptop), or team partial outage.",
        "- P3: single user partially blocked (e.g. one app access pending). "
        "New-hire access requests default to P3 unless laptop is missing.",
        "- P4: requests, preferences, cosmetic.",
        "## Response and resolution targets",
        "- P1: response 15min, resolution 2h.",
        "- P2: response 2h, resolution 8h.",
        "- P3: response 8h, resolution 48h.",
        "- P4: response 48h, resolution 1wk.",
        "## Escalation",
        "- Any P3 open >48h: auto-escalate to IT Lead via comment on "
        "the ticket.",
        "- Any new-hire ticket open >24h on Day 1: notify HR partner.",
    ])

    postmortem = _gdoc("GD105", "Slack Outage Postmortem 2026-04-22", [
        "# Slack Outage Postmortem - 2026-04-22",
        "Author: Sam Chen. Status: complete. Last edited: 2026-04-23.",
        "## What happened",
        "On 2026-04-22 at 09:14 PT, NorthHill's Okta IdP rotated a SAML "
        "signing certificate without coordinating the new public key with "
        "Slack. All Slack workspace SSO sign-ins began failing. Outage "
        "lasted ~40 minutes (resolved 09:54 PT) when the new cert was "
        "registered with Slack admin.",
        "## Customer / user impact",
        "- All 250 employees blocked from Slack for ~40 min.",
        "- Two new hires whose Day 1 was 2026-04-22 (Priya Wong and "
        "Marcus Davis) had their first-day onboarding (Slack walkthrough, "
        "buddy intros) delayed by ~1 hour.",
        "- No customer-facing impact (Slack is internal-only).",
        "## Root cause",
        "Okta's automated cert rotation policy was enabled without the "
        "matching automated push to Slack admin. Manual sync was the "
        "documented procedure but not on the rotation runbook.",
        "## Action items",
        "- [sam] Add Slack-cert-push to the Okta rotation runbook. "
        "Done 2026-04-25.",
        "- [diana] On any Day-1 SSO outage, send delayed-start guidance "
        "to affected new hires within 30min.",
        "- [it] Create a P1 ticket template for 'Workspace SSO down' so "
        "the response time hits SLA.",
    ])

    (owned / "2026-05-10_Onboarding_Playbook__GD101.gdoc.json").write_text(
        json.dumps(playbook, indent=2))
    (owned / "2026-05-10_IT_Runbook_New_Hire_Provisioning__GD102.gdoc.json"
     ).write_text(json.dumps(runbook, indent=2))
    (owned / "2026-05-12_Platform_Team_Welcome__GD103.gdoc.json").write_text(
        json.dumps(welcome, indent=2))
    (owned / "2026-05-08_IT_SLA_Matrix__GD104.gdoc.json").write_text(
        json.dumps(sla, indent=2))
    (owned / "2026-04-22_Slack_Outage_Postmortem__GD105.gdoc.json").write_text(
        json.dumps(postmortem, indent=2))


def _ticket(tid: str,
            subject: str,
            body: str,
            requester: dict,
            queue: str,
            status: str,
            priority: str,
            created_at: str,
            updated_at: str,
            assignee: dict | None = None,
            tags: list[str] | None = None,
            related_tickets: list[str] | None = None,
            comments: list[dict] | None = None) -> dict:
    return {
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


def _user_obj(handle: str) -> dict:
    u = next(u for u in USERS if u["handle"] == handle)
    return {"id": u["id"], "name": u["name"], "email": u["email"]}


def write_tickets(root: Path) -> None:
    """Materialize the IT helpdesk ticket queue on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    tickets_root = root / "tickets"
    if tickets_root.exists():
        shutil.rmtree(tickets_root)
    queue = tickets_root / "queues" / "it-helpdesk"
    (queue / "open").mkdir(parents=True, exist_ok=True)
    (queue / "in_progress").mkdir(parents=True, exist_ok=True)
    (queue / "resolved").mkdir(parents=True, exist_ok=True)
    (tickets_root / "draft").mkdir(parents=True, exist_ok=True)

    open_tickets = [
        _ticket(
            "INC-1001",
            "Laptop not arrived for Alex Rivera (Day 1)",
            "Alex Rivera starts 2026-05-12. Asset MBP-2026-014 is showing "
            "'in-shipping' in Equipment Inventory (sheet SH102). Loaner "
            "MBP-2026-LOAN-007 assigned in the meantime. Real machine "
            "expected to land Wed 2026-05-14.",
            _user_obj("alex"),
            "it-helpdesk",
            "open",
            "P2",
            "2026-05-11T14:02:11Z",
            "2026-05-12T09:14:32Z",
            assignee=_user_obj("priya"),
            tags=["onboarding", "hardware", "laptop"],
            related_tickets=["INC-1003"],
            comments=[
                {
                    "author":
                    "U104",
                    "ts":
                    "2026-05-12T09:14:32Z",
                    "body":
                    "Loaner MBP-2026-LOAN-007 handed off at IT desk. "
                    "Real device tracking shows out-for-delivery."
                },
            ],
        ),
        _ticket(
            "INC-1002",
            "AWS access request for Alex Rivera (Platform)",
            "New hire on Platform team needs IAM role for "
            "northhill-platform-prod (per Access Matrix sheet SH103, role "
            "'Software Engineer / Platform'). Gates on Okta SSO "
            "(see INC-1003).",
            _user_obj("alex"),
            "it-helpdesk",
            "open",
            "P3",
            "2026-05-12T08:43:00Z",
            "2026-05-12T08:43:00Z",
            assignee=None,
            tags=["onboarding", "access", "aws"],
            related_tickets=["INC-1003", "INC-1006"],
        ),
        _ticket(
            "INC-1004",
            "GitHub org invite for Alex Rivera (northhill-platform)",
            "Per Access Matrix (sheet SH103), Software Engineer / Platform "
            "role requires membership in github.com/northhill-platform. Send "
            "invite to alex.rivera@northhill.com and close once accepted "
            "(per IT Runbook GD102).",
            _user_obj("alex"),
            "it-helpdesk",
            "open",
            "P3",
            "2026-05-12T08:51:00Z",
            "2026-05-12T08:51:00Z",
            assignee=None,
            tags=["onboarding", "access", "github"],
        ),
        _ticket(
            "INC-1005",
            "VPN credentials expired for Bob Lee",
            "Bob's VPN client returns auth error 'credentials expired'. "
            "Last password rotation was 90 days ago per policy. Reset "
            "via Okta self-service should resolve.",
            _user_obj("bob"),
            "it-helpdesk",
            "open",
            "P3",
            "2026-05-10T22:14:00Z",
            "2026-05-11T08:00:00Z",
            assignee=_user_obj("priya"),
            tags=["vpn", "auth"],
        ),
        _ticket(
            "INC-1006",
            "Slack workspace access for Alex Rivera",
            "Need access to the NorthHill slack workspace. (Note: this is "
            "automatic via Okta SSO once INC-1003 lands - this ticket is "
            "likely a near-duplicate of INC-1002 / can be closed once "
            "SSO completes.)",
            _user_obj("alex"),
            "it-helpdesk",
            "open",
            "P3",
            "2026-05-12T08:55:00Z",
            "2026-05-12T08:55:00Z",
            assignee=None,
            tags=["onboarding", "access", "slack"],
            related_tickets=["INC-1002", "INC-1003"],
        ),
        _ticket(
            "INC-1007",
            "Office printer (3rd floor) jammed",
            "Paper jam, need someone to swing by and clear it.",
            _user_obj("priya"),
            "it-helpdesk",
            "open",
            "P4",
            "2026-05-12T11:20:00Z",
            "2026-05-12T11:20:00Z",
            assignee=None,
            tags=["facilities", "printer"],
        ),
    ]
    in_progress_tickets = [
        _ticket(
            "INC-1003",
            "Okta SSO provisioning for Alex Rivera",
            "New hire on Platform team. Provision Okta user, add to "
            "platform-eng group (which gates AWS, Slack, GitHub). Per "
            "IT Runbook GD102, Slack workspace access flows automatically "
            "from this.",
            _user_obj("alex"),
            "it-helpdesk",
            "in_progress",
            "P2",
            "2026-05-11T17:00:00Z",
            "2026-05-12T08:30:00Z",
            assignee=_user_obj("priya"),
            tags=["onboarding", "access", "sso", "okta"],
            related_tickets=["INC-1002", "INC-1004", "INC-1006"],
            comments=[
                {
                    "author":
                    "U104",
                    "ts":
                    "2026-05-12T08:30:00Z",
                    "body":
                    "User created in Okta, added to platform-eng "
                    "group. Waiting on group sync (typically <60min)."
                },
            ],
        ),
    ]
    resolved_tickets = [
        _ticket(
            "INC-0998",
            "VPN client crash for Bob Lee",
            "VPN client kept crashing on connect. Resolved by reinstalling "
            "client and clearing local profile.",
            _user_obj("bob"),
            "it-helpdesk",
            "resolved",
            "P3",
            "2026-04-15T10:00:00Z",
            "2026-04-15T16:30:00Z",
            assignee=_user_obj("priya"),
            tags=["vpn"],
            comments=[
                {
                    "author": "U104",
                    "ts": "2026-04-15T16:30:00Z",
                    "body": "Reinstalled. Verified working."
                },
            ],
        ),
        _ticket(
            "INC-0999",
            "Day-1 laptop setup for Priya Wong",
            "Provision MBP-2026-011 for new hire on IT team starting "
            "2026-04-22. Standard image + Okta enrollment. Note: "
            "completed despite the 09:14 SSO outage that day; loaner not "
            "needed.",
            _user_obj("priya"),
            "it-helpdesk",
            "resolved",
            "P2",
            "2026-04-21T09:00:00Z",
            "2026-04-22T16:00:00Z",
            assignee=_user_obj("priya"),
            tags=["onboarding", "hardware"],
            comments=[
                {
                    "author":
                    "U104",
                    "ts":
                    "2026-04-22T16:00:00Z",
                    "body":
                    "Setup complete. 1h delay due to SSO outage; "
                    "see postmortem GD105."
                },
            ],
        ),
    ]

    def _slug(s: str) -> str:
        out = []
        for ch in s.lower().strip():
            if ch.isalnum():
                out.append(ch)
            elif ch in (" ", "-", "_"):
                out.append("_")
        slug = "".join(out)
        while "__" in slug:
            slug = slug.replace("__", "_")
        return slug.strip("_")[:32] or "ticket"

    for t in open_tickets:
        fname = f"{t['ticket_id']}__{_slug(t['subject'])}.json"
        (queue / "open" /
         fname).write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n")
    for t in in_progress_tickets:
        fname = f"{t['ticket_id']}__{_slug(t['subject'])}.json"
        (queue / "in_progress" /
         fname).write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n")
    for t in resolved_tickets:
        fname = f"{t['ticket_id']}__{_slug(t['subject'])}.json"
        (queue / "resolved" /
         fname).write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n")


def main(root: str | Path = DEFAULT_ROOT, *, clean: bool = True) -> Path:
    """Seed the synthetic NorthHill corpus on disk and return the root path.

    Args:
        root (str | Path): Destination directory for the synthetic
            workspace.
        clean (bool): If True (default), wipe the root before seeding.
    """
    target = Path(root).expanduser().resolve()
    if clean and target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    write_slack(target)
    write_sheets(target)
    write_docs(target)
    write_tickets(target)
    return target


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the NorthHill onboarding+IT helpdesk corpus on disk.")
    parser.add_argument("--root",
                        default=DEFAULT_ROOT,
                        help=f"Synthetic root (default {DEFAULT_ROOT}).")
    parser.add_argument("--no-clean",
                        action="store_true",
                        help="Do not wipe the root before seeding.")
    args = parser.parse_args()
    target = main(args.root, clean=not args.no_clean)
    n = sum(1 for _ in target.rglob("*") if _.is_file())
    print(f"seeded {n} files into {target}")


if __name__ == "__main__":
    _cli()
