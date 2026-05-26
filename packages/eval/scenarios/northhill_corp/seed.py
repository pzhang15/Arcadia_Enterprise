import argparse
import csv
import io
import json
import random
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker as FakerClass
from scenarios.northhill_corp.generators import (generate_ambient_messages,
                                                 generate_customers,
                                                 generate_employees,
                                                 generate_support_tickets)

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
        "handle": "bob_lee",
        "name": "Bob Lee",
        "email": "bob.lee@northhill.com",
        "title": "Software Engineer"
    },
    {
        "id": "U201",
        "handle": "frank",
        "name": "Frank Osei",
        "email": "frank.osei@northhill.com",
        "title": "Backend Engineer"
    },
    {
        "id": "U202",
        "handle": "nina",
        "name": "Nina Gupta",
        "email": "nina.gupta@northhill.com",
        "title": "SRE"
    },
    {
        "id": "U203",
        "handle": "derek",
        "name": "Derek Wong",
        "email": "derek.wong@northhill.com",
        "title": "Security Analyst"
    },
    {
        "id": "U204",
        "handle": "lisa",
        "name": "Lisa Chen",
        "email": "lisa.chen@northhill.com",
        "title": "HR Director"
    },
    {
        "id": "U205",
        "handle": "tom",
        "name": "Tom Bradley",
        "email": "tom.bradley@northhill.com",
        "title": "Recruiter"
    },
    {
        "id": "U206",
        "handle": "rachel",
        "name": "Rachel Nguyen",
        "email": "rachel.nguyen@northhill.com",
        "title": "Finance Director"
    },
    {
        "id": "U207",
        "handle": "james_m",
        "name": "James Morrison",
        "email": "james.morrison@northhill.com",
        "title": "Accounts Payable"
    },
    {
        "id": "U208",
        "handle": "sarah_k",
        "name": "Sarah Kim",
        "email": "sarah.kim@northhill.com",
        "title": "Financial Analyst"
    },
    {
        "id": "U209",
        "handle": "maya",
        "name": "Maya Krishnan",
        "email": "maya.krishnan@northhill.com",
        "title": "Support Lead"
    },
    {
        "id": "U210",
        "handle": "carlos",
        "name": "Carlos Ruiz",
        "email": "carlos.ruiz@northhill.com",
        "title": "Support Agent"
    },
    {
        "id": "U211",
        "handle": "emily",
        "name": "Emily Zhang",
        "email": "emily.zhang@northhill.com",
        "title": "Customer Success Manager"
    },
    {
        "id": "U212",
        "handle": "bob_m",
        "name": "Bob Martinez",
        "email": "bob.martinez@northhill.com",
        "title": "SRE Lead"
    },
    {
        "id": "U213",
        "handle": "iris",
        "name": "Iris Petrova",
        "email": "iris.petrova@northhill.com",
        "title": "SRE Engineer"
    },
    {
        "id": "U214",
        "handle": "david",
        "name": "David Park",
        "email": "david.park@northhill.com",
        "title": "DevOps Engineer"
    },
    {
        "id": "U215",
        "handle": "anna",
        "name": "Anna Schmidt",
        "email": "anna.schmidt@northhill.com",
        "title": "Architect"
    },
    {
        "id": "U216",
        "handle": "michael",
        "name": "Michael Torres",
        "email": "michael.torres@northhill.com",
        "title": "Legal Counsel"
    },
    {
        "id": "U217",
        "handle": "jennifer",
        "name": "Jennifer Wu",
        "email": "jennifer.wu@northhill.com",
        "title": "Compliance Manager"
    },
    {
        "id": "U218",
        "handle": "patricia",
        "name": "Patricia Chen",
        "email": "patricia.chen@northhill.com",
        "title": "VP Engineering"
    },
    {
        "id": "U219",
        "handle": "robert",
        "name": "Robert Singh",
        "email": "robert.singh@northhill.com",
        "title": "COO"
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
    {
        "id": "C306",
        "name": "finance"
    },
    {
        "id": "C307",
        "name": "customer-support"
    },
    {
        "id": "C308",
        "name": "engineering"
    },
    {
        "id": "C309",
        "name": "compliance"
    },
    {
        "id": "C310",
        "name": "leadership"
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
         "hi team! my laptop hasn't shown up yet (started today, INC-1001 "
         "filed). tracking number says it's still in transit. anything I can "
         "do from my personal machine in the meantime?"),
        ("2026-05-11", "U103", "1715460000.000100",
         "@alex hang tight - we have a loaner program. priya will hand one "
         "off by EOD. I'll bump INC-1001 priority."),
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
         "AWS + GitHub. will start on the platform setup with jordan "
         "tomorrow."),
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
        ("2026-05-15", "U212", "1715759000.000100",
         "INC-5521 triggered: payments-api P99 latency spiked to 2147ms "
         "(threshold 500ms). Error rate at 4.2%. Correlated with deployment "
         "d4e5f6 at 14:00 UTC by @frank. Opening incident bridge."),
        ("2026-05-15", "U201", "1715759200.000100",
         "Looking at the commit now. The deployment changed connection pool "
         "settings - reduced connectionPoolSize from 50 to 10. That's "
         "almost certainly the cause."),
        ("2026-05-15", "U212", "1715759400.000100",
         "Confirmed in Datadog: seeing 'connection pool exhausted' errors "
         "starting at exactly 14:00:30. 847 occurrences in the last 10 "
         "minutes. Linked ticket OPS-1247."),
        ("2026-05-15", "U218", "1715759600.000100",
         "Customer impact confirmed - GlobalTech users reporting login "
         "failures (CS-1001). Rolling back deployment now."),
    ],
    "C306": [
        ("2026-05-14", "U206", "1715680000.000100",
         "Heads up team - Q2 budget review is tomorrow (May 15). Department "
         "leads please submit your actuals by EOD today. Dashboard in sheet "
         "SH105."),
        ("2026-05-14", "U208", "1715683600.000100",
         "Engineering is at 78% of Q2 budget with 6 weeks remaining. The "
         "new server PO (PO-1003) will push us to 85%. Flagging for "
         "discussion."),
        ("2026-05-15", "U207", "1715766000.000100",
         "Reminder: expense reports for May must be submitted by May 23. "
         "Currently 6 pending reports totaling $14,200. Please approve or "
         "return promptly."),
        ("2026-05-15", "U206", "1715769600.000100",
         "PO-1003 approved for $45,000 (new database servers from "
         "CloudRack). @james_m please process. Vendor confirmed 2-week "
         "delivery."),
    ],
    "C307": [
        ("2026-05-14", "U209", "1715676000.000100",
         "Escalation: GlobalTech (ACCT-1001, enterprise tier) reporting "
         "intermittent login failures for their SSO-integrated users. "
         "CS-1001 filed as P2. @emily please check account health."),
        ("2026-05-14", "U211", "1715679600.000100",
         "GlobalTech health score dropped to 45 (was 72 last month). "
         "Renewal is in 3 months. Creating escalation ESC-1001. This "
         "needs eng attention."),
        ("2026-05-15", "U210", "1715762400.000100",
         "Update on CS-1001: confirmed linked to engineering incident "
         "INC-5521. GlobalTech's auth flow goes through our payments-api "
         "which is currently degraded. Eng is rolling back."),
        ("2026-05-15", "U209", "1715766000.000200",
         "Account health alert: PayRight (ACCT-1002) data sync delay "
         "reported. CS-1003 in progress. Not related to the payments-api "
         "incident - separate issue with their webhook integration."),
    ],
    "C308": [
        ("2026-05-14", "U214", "1715680000.000200",
         "Deployment pipeline update: migrated to GitHub Actions v4. All "
         "services now deploy via the unified pipeline. Rollback time "
         "reduced from 8min to 3min."),
        ("2026-05-15", "U212", "1715758800.000100",
         "CODE FREEZE in effect for payments-api. Do not merge until "
         "INC-5521 is resolved. Incident bridge: #incidents channel."),
        ("2026-05-15", "U215", "1715762400.000200",
         "Post-incident note: we need connection pool config to go through "
         "the capacity planning review process. Adding to the architecture "
         "review checklist."),
    ],
    "C309": [
        ("2026-05-13", "U217", "1715590000.000100",
         "SOC2 Type II audit prep: evidence collection due by June 15. "
         "AUDIT-2026-SOC2 tracking sheet is live. Department owners please "
         "review your assigned controls and upload evidence. Current "
         "progress: 8/24 controls documented."),
        ("2026-05-15", "U217", "1715770000.000100",
         "Reminder: policy acknowledgment deadline is May 20. POL-1001 "
         "(Data Handling), POL-1002 (Acceptable Use), and POL-1003 "
         "(Incident Response) all require 100% team acknowledgment. "
         "Currently at 18/28 employees."),
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
         "Got it. I noticed INC-1006 looks like a near-duplicate of "
         "INC-1002 - should I close it?"),
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
        "team": "T_NorthHill",
    }


def write_slack(
    root: Path,
    extra_users: list[dict] | None = None,
    ambient_messages: dict[str, list[tuple[str, str, str, str]]] | None = None,
) -> None:
    """Materialize Slack channels, DMs, and user profiles on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
        extra_users (list[dict] | None): Generated employees
            to write profiles for.
        ambient_messages (dict | None): Channel ID to list
            of ambient noise tuples.
    """
    all_users = USERS + (extra_users or [])
    slack_root = root / "slack"
    if slack_root.exists():
        shutil.rmtree(slack_root)

    merged_messages: dict[str, list[tuple[str, str, str, str]]] = {}
    for ch_id, msgs in CHANNEL_MESSAGES.items():
        merged_messages[ch_id] = list(msgs)
    if ambient_messages:
        for ch_id, msgs in ambient_messages.items():
            merged_messages.setdefault(ch_id, []).extend(msgs)

    for ch in CHANNELS:
        ch_dir = slack_root / "channels" / f"{ch['name']}__{ch['id']}"
        days: dict[str, list[dict]] = {}
        for date, uid, ts, text in merged_messages.get(ch["id"], []):
            days.setdefault(date, []).append(_slack_msg(uid, ts, text))
        for date, msgs in sorted(days.items()):
            msgs.sort(key=lambda m: m["ts"])
            day_dir = ch_dir / date
            day_dir.mkdir(parents=True, exist_ok=True)
            (day_dir / "files").mkdir(exist_ok=True)
            (day_dir / "chat.jsonl").write_text("\n".join(
                json.dumps(m, ensure_ascii=False) for m in msgs) + "\n")
        if not days:
            ch_dir.mkdir(parents=True, exist_ok=True)
    for dm in DMS:
        peer = next(u for u in USERS if u["handle"] == dm["with_handle"])
        dm_dir = slack_root / "dms" / f"{peer['handle']}__{dm['id']}"
        days: dict[str, list[dict]] = {}
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
    for u in all_users:
        profile = {
            "id": u["id"],
            "name": u["handle"],
            "real_name": u["name"],
            "profile": {
                "title": u["title"],
                "email": u["email"],
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
        "Name",
        "Start Date",
        "Team",
        "Manager",
        "Buddy",
        "Equipment Status",
        "Access Status",
        "Day 1 Complete",
    ],
    [
        "Alex Rivera",
        "2026-05-12",
        "Platform",
        "Marcus Johnson",
        "Jordan Kim",
        "loaner_in_use_pending_shipment",
        "in_progress",
        "N",
    ],
    [
        "Priya Wong",
        "2026-04-22",
        "IT",
        "Sam Chen",
        "Priya Patel",
        "received",
        "complete",
        "Y",
    ],
    [
        "Marcus Davis",
        "2026-04-22",
        "Platform",
        "Marcus Johnson",
        "Jordan Kim",
        "received",
        "complete",
        "Y",
    ],
    [
        "Lin Wei",
        "2026-05-19",
        "Platform",
        "Marcus Johnson",
        "Jordan Kim",
        "ordered",
        "not_started",
        "N",
    ],
]

EQUIPMENT_INVENTORY_ROWS = [
    [
        "Asset ID",
        "Type",
        "Model",
        "Serial",
        "Assigned To",
        "Location",
        "Status",
    ],
    [
        "MBP-2026-014",
        "Laptop",
        "MacBook Pro M4 14\"",
        "C02XX1Z2J1WL",
        "Alex Rivera",
        "shipping",
        "in-shipping",
    ],
    [
        "MBP-2026-LOAN-007",
        "Laptop (Loaner)",
        "MacBook Pro M3 14\"",
        "C02LO0AN3WL",
        "Alex Rivera",
        "office-sf",
        "assigned_loaner",
    ],
    [
        "MBP-2026-009",
        "Laptop",
        "MacBook Pro M4 14\"",
        "C02XX1Z2J1WK",
        "Bob Lee",
        "office-sf",
        "assigned",
    ],
    [
        "MBP-2026-011",
        "Laptop",
        "MacBook Pro M4 14\"",
        "C02XX1Z2J1WJ",
        "Priya Wong",
        "office-sf",
        "assigned",
    ],
    [
        "DELL-MON-022",
        "Monitor",
        "Dell U2723QE",
        "MON022",
        "",
        "office-sf",
        "in-stock",
    ],
    [
        "MBP-2026-022",
        "Laptop",
        "MacBook Pro M4 14\"",
        "C02FUTURE0JE",
        "Lin Wei",
        "warehouse",
        "ordered",
    ],
]

ACCESS_MATRIX_ROWS = [
    [
        "Role",
        "Team",
        "GitHub Org",
        "Slack Channels",
        "AWS Account",
        "Postgres DB",
        "Notion",
        "Linear Team",
    ],
    [
        "Software Engineer",
        "Platform",
        "northhill-platform",
        "platform-team,eng,general",
        "northhill-platform-prod",
        "platform_db",
        "Engineering",
        "Platform",
    ],
    [
        "Software Engineer",
        "IT",
        "northhill-it",
        "it-helpdesk,eng,general",
        "northhill-it-prod",
        "ops_db",
        "IT",
        "IT",
    ],
    [
        "IT Lead",
        "IT",
        "northhill-it,northhill-org-admin",
        "it-helpdesk,eng,general,leadership",
        "northhill-it-prod,northhill-billing",
        "ops_db,billing_db",
        "IT,Leadership",
        "IT",
    ],
    [
        "HR Partner",
        "People",
        "(none)",
        "onboarding,general,people-ops",
        "(none)",
        "(none)",
        "People,All-hands",
        "People",
    ],
]

PTO_CALENDAR_ROWS = [
    [
        "Name",
        "Department",
        "Request Date",
        "Start",
        "End",
        "Days",
        "Status",
        "Approver",
    ],
    [
        "Jordan Kim",
        "Platform",
        "2026-05-10",
        "2026-05-19",
        "2026-05-21",
        "3",
        "approved",
        "Marcus Johnson",
    ],
    [
        "Carlos Ruiz",
        "Customer Support",
        "2026-05-08",
        "2026-05-26",
        "2026-05-30",
        "5",
        "approved",
        "Maya Krishnan",
    ],
    [
        "James Morrison",
        "Finance",
        "2026-05-12",
        "2026-06-02",
        "2026-06-06",
        "5",
        "pending",
        "Rachel Nguyen",
    ],
    [
        "Derek Wong",
        "IT",
        "2026-05-14",
        "2026-06-09",
        "2026-06-10",
        "2",
        "approved",
        "Sam Chen",
    ],
    [
        "Anna Schmidt",
        "Engineering/SRE",
        "2026-05-11",
        "2026-05-22",
        "2026-05-23",
        "2",
        "pending",
        "Patricia Chen",
    ],
]

DEPARTMENT_BUDGET_ROWS = [
    ["Department", "Q2 Budget", "Q2 Spent", "Q2 Remaining", "Status"],
    ["Platform Engineering", "$420,000", "$327,600", "$92,400", "on_track"],
    ["IT", "$180,000", "$142,200", "$37,800", "on_track"],
    ["People/HR", "$95,000", "$68,400", "$26,600", "on_track"],
    ["Finance", "$65,000", "$41,300", "$23,700", "on_track"],
    ["Customer Support", "$210,000", "$178,500", "$31,500", "at_risk"],
    ["Engineering/SRE", "$350,000", "$298,200", "$51,800", "on_track"],
    ["Legal/Compliance", "$120,000", "$108,600", "$11,400", "over_budget"],
    ["Executive", "$75,000", "$52,100", "$22,900", "on_track"],
]


def write_sheets(root: Path) -> None:
    """Materialize GSheet JSONs on disk.

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
    pto = _gsheet("SH104", "PTO Calendar",
                  [_tab(0, "Requests", PTO_CALENDAR_ROWS)])
    budget = _gsheet("SH105", "Department Budget",
                     [_tab(0, "Q2 2026", DEPARTMENT_BUDGET_ROWS)])

    (owned / "2026-05-12_New_Hire_Tracker__SH101.gsheet.json").write_text(
        json.dumps(tracker, indent=2))
    (owned /
     "2026-05-12_IT_Equipment_Inventory__SH102.gsheet.json").write_text(
         json.dumps(inventory, indent=2))
    (owned / "2026-05-12_Access_Matrix__SH103.gsheet.json").write_text(
        json.dumps(access, indent=2))
    (owned / "2026-05-12_PTO_Calendar__SH104.gsheet.json").write_text(
        json.dumps(pto, indent=2))
    (owned / "2026-05-14_Department_Budget__SH105.gsheet.json").write_text(
        json.dumps(budget, indent=2))


def _gdoc(did: str, title: str, paragraphs: list[str]) -> dict:
    content = []
    for p in paragraphs:
        content.append({
            "paragraph": {
                "elements": [{
                    "textRun": {
                        "content": p + "\n",
                        "textStyle": {},
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
    """Materialize GDoc JSONs on disk.

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
        "- Pick up laptop from IT desk "
        "(or arrange loaner if not yet shipped).",
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

    expense_policy = _gdoc("GD106", "Expense Policy", [
        "# NorthHill Corp Expense Reimbursement Policy",
        "Owner: Rachel Nguyen (Finance Director). Effective: 2026-01-01.",
        "## General rules",
        "- All expenses must be submitted within 30 days of incurrence.",
        "- Receipts required for any expense over $25.",
        "- Expenses must be categorized: travel, software, meals, equipment, "
        "or other.",
        "## Approval thresholds",
        "- Under $500: direct manager approval.",
        "- $500 - $5,000: department head + Finance Director approval.",
        "- Over $5,000: VP-level + CFO approval.",
        "## Travel",
        "- Airfare: economy class for domestic, premium economy for "
        "international flights over 6 hours.",
        "- Hotels: up to $250/night domestic, $350/night international.",
        "- Meals: up to $75/day (individual) or $150/person (client meals).",
        "## Software",
        "- SaaS subscriptions under $50/month: manager approval.",
        "- Annual subscriptions or tools over $50/month: must go through "
        "procurement (see Vendor Management Policy GD107).",
    ])

    vendor_policy = _gdoc("GD107", "Vendor Management Policy", [
        "# NorthHill Corp Vendor Management Policy",
        "Owner: Rachel Nguyen (Finance Director). Effective: 2026-01-01.",
        "## Procurement process",
        "- All vendor engagements over $10,000 require a purchase order.",
        "- POs must reference an approved budget line item.",
        "- Vendor security assessment required for any vendor handling "
        "customer data (coordinate with compliance team).",
        "## Approved vendors",
        "- CloudRack Inc. (infrastructure/hosting)",
        "- DataFlow Systems (data pipeline tooling)",
        "- SecureSign Corp (e-signature platform)",
        "- NetGuard Solutions (network security)",
        "## New vendor onboarding",
        "- Submit vendor request via finance channel.",
        "- Legal reviews contract terms (NDA required first).",
        "- Compliance reviews data handling practices.",
        "- Finance issues PO upon all approvals.",
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
    (owned / "2026-01-01_Expense_Policy__GD106.gdoc.json").write_text(
        json.dumps(expense_policy, indent=2))
    (owned /
     "2026-01-01_Vendor_Management_Policy__GD107.gdoc.json").write_text(
         json.dumps(vendor_policy, indent=2))


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
            comments: list[dict] | None = None,
            severity: str | None = None,
            linked_incidents: list[str] | None = None) -> dict:
    t: dict = {
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
    return t


def _user_obj(handle: str) -> dict:
    u = next(u for u in USERS if u["handle"] == handle)
    return {"id": u["id"], "name": u["name"], "email": u["email"]}


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


def _write_tickets_to_dir(queue_dir: Path, status: str,
                          tickets: list[dict]) -> None:
    for t in tickets:
        fname = f"{t['ticket_id']}__{_slug(t['subject'])}.json"
        (queue_dir / status /
         fname).write_text(json.dumps(t, indent=2, ensure_ascii=False) + "\n")


def write_tickets(
    root: Path,
    extra_cs_tickets: list[dict] | None = None,
) -> None:
    """Materialize ticket queues on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
        extra_cs_tickets (list[dict] | None): Generated
            customer support tickets.
    """
    tickets_root = root / "tickets"
    if tickets_root.exists():
        shutil.rmtree(tickets_root)
    (tickets_root / "draft").mkdir(parents=True, exist_ok=True)

    it_q = tickets_root / "queues" / "it-helpdesk"
    for s in ("open", "in_progress", "resolved"):
        (it_q / s).mkdir(parents=True, exist_ok=True)

    it_open = [
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
            comments=[{
                "author":
                "U104",
                "ts":
                "2026-05-12T09:14:32Z",
                "body":
                "Loaner MBP-2026-LOAN-007 handed off at IT desk. "
                "Real device tracking shows out-for-delivery.",
            }],
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
            tags=["onboarding", "access", "github"],
        ),
        _ticket(
            "INC-1005",
            "VPN credentials expired for Bob Lee",
            "Bob's VPN client returns auth error 'credentials expired'. "
            "Last password rotation was 90 days ago per policy. Reset "
            "via Okta self-service should resolve.",
            _user_obj("bob_lee"),
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
            tags=["facilities", "printer"],
        ),
    ]
    it_in_progress = [
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
            comments=[{
                "author":
                "U104",
                "ts":
                "2026-05-12T08:30:00Z",
                "body":
                "User created in Okta, added to platform-eng "
                "group. Waiting on group sync (typically <60min).",
            }],
        ),
    ]
    it_resolved = [
        _ticket(
            "INC-0998",
            "VPN client crash for Bob Lee",
            "VPN client kept crashing on connect. Resolved by reinstalling "
            "client and clearing local profile.",
            _user_obj("bob_lee"),
            "it-helpdesk",
            "resolved",
            "P3",
            "2026-04-15T10:00:00Z",
            "2026-04-15T16:30:00Z",
            assignee=_user_obj("priya"),
            tags=["vpn"],
            comments=[{
                "author": "U104",
                "ts": "2026-04-15T16:30:00Z",
                "body": "Reinstalled. Verified working.",
            }],
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
            comments=[{
                "author":
                "U104",
                "ts":
                "2026-04-22T16:00:00Z",
                "body":
                "Setup complete. 1h delay due to SSO outage; "
                "see postmortem GD105.",
            }],
        ),
    ]
    _write_tickets_to_dir(it_q, "open", it_open)
    _write_tickets_to_dir(it_q, "in_progress", it_in_progress)
    _write_tickets_to_dir(it_q, "resolved", it_resolved)

    cs_q = tickets_root / "queues" / "customer-support"
    for s in ("open", "in_progress", "resolved"):
        (cs_q / s).mkdir(parents=True, exist_ok=True)

    cs_open = [
        _ticket(
            "CS-1001",
            "Login failures for GlobalTech users",
            "GlobalTech (ACCT-1001, enterprise tier) reporting intermittent "
            "login failures for SSO-integrated users since 14:00 UTC. "
            "Linked to engineering incident INC-5521 (payments-api P99 "
            "latency spike). Escalation ESC-1001 created. Account health "
            "score dropped to 45.",
            {
                "id": "external",
                "name": "GlobalTech Support",
                "email": "support@globaltech.com"
            },
            "customer-support",
            "open",
            "P2",
            "2026-05-15T14:15:00Z",
            "2026-05-15T14:45:00Z",
            assignee=_user_obj("maya"),
            tags=["escalation", "sso", "enterprise"],
            related_tickets=["OPS-1247"],
            linked_incidents=["INC-5521"],
            comments=[{
                "author":
                "U210",
                "ts":
                "2026-05-15T14:30:00Z",
                "body":
                "Confirmed linked to INC-5521. Eng is rolling back "
                "deployment d4e5f6. ETA for resolution: 30min.",
            }],
        ),
        _ticket(
            "CS-1002",
            "Feature request: bulk export API",
            "Multiple customers have requested a bulk data export API "
            "endpoint. Currently they must export page-by-page which is "
            "impractical for large datasets. Logging as feature request.",
            {
                "id": "external",
                "name": "PayRight PM",
                "email": "pm@payright.io"
            },
            "customer-support",
            "open",
            "P4",
            "2026-05-13T10:00:00Z",
            "2026-05-13T10:00:00Z",
            tags=["feature-request", "api"],
        ),
        _ticket(
            "CS-1004",
            "Billing discrepancy for TechFlow",
            "TechFlow (ACCT-1003) reports invoice INV-3001 shows charges "
            "for 150 seats but their contract is for 120 seats. Need "
            "finance to verify against contract CTR-1004.",
            {
                "id": "external",
                "name": "TechFlow Billing",
                "email": "billing@techflow.dev"
            },
            "customer-support",
            "open",
            "P3",
            "2026-05-14T16:00:00Z",
            "2026-05-14T16:00:00Z",
            assignee=_user_obj("emily"),
            tags=["billing", "enterprise"],
            related_tickets=["INV-3001"],
        ),
    ]
    cs_in_progress = [
        _ticket(
            "CS-1003",
            "Data sync delay for PayRight",
            "PayRight (ACCT-1002, pro tier) reporting webhook delivery "
            "delays of up to 15 minutes. Their integration depends on "
            "near-realtime event delivery. Investigating webhook "
            "queue health.",
            {
                "id": "external",
                "name": "PayRight Engineering",
                "email": "eng@payright.io"
            },
            "customer-support",
            "in_progress",
            "P2",
            "2026-05-14T11:00:00Z",
            "2026-05-15T09:00:00Z",
            assignee=_user_obj("carlos"),
            tags=["webhook", "data-sync", "pro"],
            comments=[{
                "author":
                "U210",
                "ts":
                "2026-05-15T09:00:00Z",
                "body":
                "Isolated to PayRight's webhook endpoint. Their "
                "endpoint is responding slowly (avg 8s). Working "
                "with their eng team on a fix.",
            }],
        ),
    ]
    cs_resolved = [
        _ticket(
            "CS-1005",
            "Onboarding assistance for NovaCorp",
            "NovaCorp (ACCT-1004, starter tier) needed help with initial "
            "API integration setup. Walked them through auth flow and "
            "webhook configuration. All endpoints verified working.",
            {
                "id": "external",
                "name": "NovaCorp Dev",
                "email": "dev@novacorp.io"
            },
            "customer-support",
            "resolved",
            "P3",
            "2026-05-10T14:00:00Z",
            "2026-05-12T10:00:00Z",
            assignee=_user_obj("carlos"),
            tags=["onboarding", "starter"],
            comments=[{
                "author":
                "U210",
                "ts":
                "2026-05-12T10:00:00Z",
                "body":
                "Integration complete. NovaCorp confirmed all "
                "endpoints are working. Closing.",
            }],
        ),
    ]
    _write_tickets_to_dir(cs_q, "open", cs_open)
    _write_tickets_to_dir(cs_q, "in_progress", cs_in_progress)
    _write_tickets_to_dir(cs_q, "resolved", cs_resolved)

    if extra_cs_tickets:
        gen_employees = generate_employees(seed=42)
        all_u = USERS + gen_employees
        for gen_t in extra_cs_tickets:
            assignee_handle = gen_t.pop("assignee_handle", None)
            gen_t.pop("account_id", None)
            assignee = None
            if assignee_handle:
                match = next(
                    (u for u in all_u if u["handle"] == assignee_handle), None)
                if match:
                    assignee = {
                        "id": match["id"],
                        "name": match["name"],
                        "email": match["email"]
                    }
            t = _ticket(
                gen_t["ticket_id"],
                gen_t["subject"],
                gen_t["body"],
                gen_t["requester"],
                gen_t["queue"],
                gen_t["status"],
                gen_t["priority"],
                gen_t["created_at"],
                gen_t["updated_at"],
                assignee=assignee,
                tags=gen_t.get("tags", []),
                related_tickets=gen_t.get("related_tickets", []),
                comments=gen_t.get("comments", []),
            )
            _write_tickets_to_dir(cs_q, t["status"], [t])

    legal_q = tickets_root / "queues" / "legal"
    for s in ("open", "in_progress", "resolved"):
        (legal_q / s).mkdir(parents=True, exist_ok=True)

    legal_open = [
        _ticket(
            "LGL-1001",
            "NDA review for CloudBase partnership",
            "CloudBase (ACCT-1006) proposing a strategic partnership. "
            "Need NDA reviewed and signed before technical evaluation "
            "can proceed. Draft NDA attached by CloudBase legal team.",
            _user_obj("emily"),
            "legal",
            "open",
            "P3",
            "2026-05-13T09:00:00Z",
            "2026-05-13T09:00:00Z",
            assignee=_user_obj("michael"),
            tags=["nda", "partnership", "contract"],
        ),
        _ticket(
            "LGL-1003",
            "GDPR data deletion request from EU customer",
            "EU-based customer (DataVault, ACCT-1005) submitted formal "
            "GDPR Article 17 right-to-erasure request. 30-day compliance "
            "deadline from receipt date (2026-05-14). Need to coordinate "
            "with engineering for data purge across all systems.",
            {
                "id": "external",
                "name": "DataVault DPO",
                "email": "dpo@datavault.eu"
            },
            "legal",
            "open",
            "P1",
            "2026-05-14T08:00:00Z",
            "2026-05-14T08:00:00Z",
            assignee=_user_obj("jennifer"),
            tags=["gdpr", "data-deletion", "compliance"],
        ),
    ]
    legal_in_progress = [
        _ticket(
            "LGL-1002",
            "SOC2 audit evidence collection",
            "SOC2 Type II audit (AUDIT-2026-SOC2) evidence collection "
            "in progress. Due date: 2026-06-15. Currently 8/24 controls "
            "documented. Need department owners to upload remaining "
            "evidence to compliance/audits/ directory.",
            _user_obj("jennifer"),
            "legal",
            "in_progress",
            "P2",
            "2026-05-01T09:00:00Z",
            "2026-05-15T10:00:00Z",
            assignee=_user_obj("jennifer"),
            tags=["soc2", "audit", "compliance"],
            comments=[{
                "author":
                "U217",
                "ts":
                "2026-05-15T10:00:00Z",
                "body":
                "8/24 controls documented. Blockers: engineering "
                "change management evidence (waiting on David), "
                "HR background check policy (waiting on Lisa).",
            }],
        ),
    ]
    _write_tickets_to_dir(legal_q, "open", legal_open)
    _write_tickets_to_dir(legal_q, "in_progress", legal_in_progress)


def write_finance(root: Path) -> None:
    """Materialize finance data (expenses, POs, invoices, budgets) on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    fin_root = root / "finance"
    if fin_root.exists():
        shutil.rmtree(fin_root)

    for sub in ("expenses/pending", "expenses/approved", "expenses/rejected",
                "purchase_orders/open", "purchase_orders/approved",
                "purchase_orders/received", "invoices/pending",
                "invoices/paid", "invoices/disputed", "budgets"):
        (fin_root / sub).mkdir(parents=True, exist_ok=True)

    pending_expenses = [
        {
            "expense_id":
            "EXP-1001",
            "submitter":
            _user_obj("frank"),
            "department":
            "Platform Engineering",
            "amount":
            1250.00,
            "currency":
            "USD",
            "category":
            "travel",
            "description":
            "Flight + hotel for PlatformCon 2026 (San Francisco)",
            "receipt_url":
            "/finance/receipts/EXP-1001_receipt.pdf",
            "submitted_at":
            "2026-05-10T09:00:00Z",
            "status":
            "pending",
            "approver":
            None,
            "line_items": [
                {
                    "description": "Round-trip flight SFO",
                    "amount": 450.00
                },
                {
                    "description": "Hotel (2 nights)",
                    "amount": 500.00
                },
                {
                    "description": "Meals (2 days)",
                    "amount": 150.00
                },
                {
                    "description": "Ground transport",
                    "amount": 150.00
                },
            ],
        },
        {
            "expense_id":
            "EXP-1002",
            "submitter":
            _user_obj("iris"),
            "department":
            "Engineering/SRE",
            "amount":
            89.99,
            "currency":
            "USD",
            "category":
            "software",
            "description":
            "Datadog Pro license upgrade (monthly)",
            "receipt_url":
            "/finance/receipts/EXP-1002_receipt.pdf",
            "submitted_at":
            "2026-05-11T14:30:00Z",
            "status":
            "pending",
            "approver":
            None,
            "line_items": [
                {
                    "description": "Datadog Pro monthly subscription",
                    "amount": 89.99
                },
            ],
        },
        {
            "expense_id":
            "EXP-1003",
            "submitter":
            _user_obj("david"),
            "department":
            "Engineering/SRE",
            "amount":
            3200.00,
            "currency":
            "USD",
            "category":
            "equipment",
            "description":
            "Replacement NVMe drives for staging cluster "
            "(related to PO-1002 from CloudRack)",
            "receipt_url":
            "/finance/receipts/EXP-1003_receipt.pdf",
            "submitted_at":
            "2026-05-12T10:00:00Z",
            "status":
            "pending",
            "approver":
            None,
            "line_items": [
                {
                    "description": "Samsung 990 PRO 2TB NVMe x4",
                    "amount": 3200.00
                },
            ],
        },
        {
            "expense_id":
            "EXP-1004",
            "submitter":
            _user_obj("maya"),
            "department":
            "Customer Support",
            "amount":
            4500.00,
            "currency":
            "USD",
            "category":
            "software",
            "description":
            "Zendesk annual plan renewal (team of 3)",
            "receipt_url":
            "/finance/receipts/EXP-1004_receipt.pdf",
            "submitted_at":
            "2026-05-13T08:00:00Z",
            "status":
            "pending",
            "approver":
            None,
            "line_items": [
                {
                    "description": "Zendesk Professional (3 seats, annual)",
                    "amount": 4500.00
                },
            ],
        },
        {
            "expense_id":
            "EXP-1005",
            "submitter":
            _user_obj("tom"),
            "department":
            "People/HR",
            "amount":
            275.00,
            "currency":
            "USD",
            "category":
            "meals",
            "description":
            "Team lunch for new hire welcome (8 attendees)",
            "receipt_url":
            "/finance/receipts/EXP-1005_receipt.pdf",
            "submitted_at":
            "2026-05-12T16:00:00Z",
            "status":
            "pending",
            "approver":
            None,
            "line_items": [
                {
                    "description": "Team lunch (8 people)",
                    "amount": 275.00
                },
            ],
        },
        {
            "expense_id":
            "EXP-1006",
            "submitter":
            _user_obj("jennifer"),
            "department":
            "Legal/Compliance",
            "amount":
            4850.00,
            "currency":
            "USD",
            "category":
            "software",
            "description":
            "Vanta compliance platform (quarterly)",
            "receipt_url":
            "/finance/receipts/EXP-1006_receipt.pdf",
            "submitted_at":
            "2026-05-14T11:00:00Z",
            "status":
            "pending",
            "approver":
            None,
            "line_items": [
                {
                    "description": "Vanta SOC2 automation (Q3 quarter)",
                    "amount": 4850.00
                },
            ],
        },
    ]
    approved_expenses = [
        {
            "expense_id":
            "EXP-0991",
            "submitter":
            _user_obj("bob_m"),
            "department":
            "Engineering/SRE",
            "amount":
            2100.00,
            "currency":
            "USD",
            "category":
            "travel",
            "description":
            "SREcon 2026 attendance (Portland)",
            "receipt_url":
            "/finance/receipts/EXP-0991_receipt.pdf",
            "submitted_at":
            "2026-04-28T09:00:00Z",
            "status":
            "approved",
            "approver":
            _user_obj("patricia"),
            "line_items": [
                {
                    "description": "Conference registration",
                    "amount": 800.00
                },
                {
                    "description": "Flight",
                    "amount": 380.00
                },
                {
                    "description": "Hotel (3 nights)",
                    "amount": 750.00
                },
                {
                    "description": "Meals",
                    "amount": 170.00
                },
            ],
        },
        {
            "expense_id":
            "EXP-0992",
            "submitter":
            _user_obj("sam"),
            "department":
            "IT",
            "amount":
            620.00,
            "currency":
            "USD",
            "category":
            "equipment",
            "description":
            "Replacement keyboards and mice (IT stock)",
            "receipt_url":
            "/finance/receipts/EXP-0992_receipt.pdf",
            "submitted_at":
            "2026-05-02T10:00:00Z",
            "status":
            "approved",
            "approver":
            _user_obj("rachel"),
            "line_items": [
                {
                    "description": "Apple Magic Keyboard x5",
                    "amount": 500.00
                },
                {
                    "description": "Logitech MX Master 3S x2",
                    "amount": 120.00
                },
            ],
        },
        {
            "expense_id":
            "EXP-0993",
            "submitter":
            _user_obj("diana"),
            "department":
            "People/HR",
            "amount":
            180.00,
            "currency":
            "USD",
            "category":
            "meals",
            "description":
            "Candidate lunch (final round interview)",
            "receipt_url":
            "/finance/receipts/EXP-0993_receipt.pdf",
            "submitted_at":
            "2026-05-05T15:00:00Z",
            "status":
            "approved",
            "approver":
            _user_obj("lisa"),
            "line_items": [
                {
                    "description": "Lunch (4 attendees)",
                    "amount": 180.00
                },
            ],
        },
        {
            "expense_id":
            "EXP-0994",
            "submitter":
            _user_obj("anna"),
            "department":
            "Engineering/SRE",
            "amount":
            49.99,
            "currency":
            "USD",
            "category":
            "software",
            "description":
            "Lucidchart monthly subscription",
            "receipt_url":
            "/finance/receipts/EXP-0994_receipt.pdf",
            "submitted_at":
            "2026-05-06T09:00:00Z",
            "status":
            "approved",
            "approver":
            _user_obj("bob_m"),
            "line_items": [
                {
                    "description": "Lucidchart Team plan (1 seat)",
                    "amount": 49.99
                },
            ],
        },
    ]
    rejected_expenses = [
        {
            "expense_id":
            "EXP-0989",
            "submitter":
            _user_obj("carlos"),
            "department":
            "Customer Support",
            "amount":
            8500.00,
            "currency":
            "USD",
            "category":
            "travel",
            "description":
            "Customer visit to GlobalTech HQ (business class)",
            "receipt_url":
            "/finance/receipts/EXP-0989_receipt.pdf",
            "submitted_at":
            "2026-04-20T09:00:00Z",
            "status":
            "rejected",
            "approver":
            _user_obj("rachel"),
            "line_items": [
                {
                    "description": "Business class flight",
                    "amount": 5200.00
                },
                {
                    "description": "Hotel (3 nights)",
                    "amount": 2100.00
                },
                {
                    "description": "Meals",
                    "amount": 1200.00
                },
            ],
        },
        {
            "expense_id":
            "EXP-0990",
            "submitter":
            _user_obj("derek"),
            "department":
            "IT",
            "amount":
            12000.00,
            "currency":
            "USD",
            "category":
            "software",
            "description":
            "CrowdStrike Falcon annual license (unapproved vendor)",
            "receipt_url":
            "/finance/receipts/EXP-0990_receipt.pdf",
            "submitted_at":
            "2026-04-25T14:00:00Z",
            "status":
            "rejected",
            "approver":
            _user_obj("rachel"),
            "line_items": [
                {
                    "description": "CrowdStrike Falcon Go (annual)",
                    "amount": 12000.00
                },
            ],
        },
    ]

    for exp in pending_expenses:
        (fin_root / "expenses" / "pending" / f"{exp['expense_id']}.json"
         ).write_text(json.dumps(exp, indent=2) + "\n")
    for exp in approved_expenses:
        (fin_root / "expenses" / "approved" / f"{exp['expense_id']}.json"
         ).write_text(json.dumps(exp, indent=2) + "\n")
    for exp in rejected_expenses:
        (fin_root / "expenses" / "rejected" / f"{exp['expense_id']}.json"
         ).write_text(json.dumps(exp, indent=2) + "\n")

    open_pos = [
        {
            "po_id":
            "PO-1001",
            "requester":
            _user_obj("sam"),
            "vendor":
            "SecureSign Corp",
            "items": [
                {
                    "description": "SecureSign Enterprise (annual)",
                    "qty": 1,
                    "unit_price": 8000.00
                },
            ],
            "total":
            8000.00,
            "status":
            "open",
            "created_at":
            "2026-05-10T09:00:00Z",
            "approved_by":
            None,
            "department":
            "IT",
        },
        {
            "po_id":
            "PO-1002",
            "requester":
            _user_obj("david"),
            "vendor":
            "CloudRack Inc.",
            "items": [
                {
                    "description": "Staging server (16-core, 64GB)",
                    "qty": 2,
                    "unit_price": 4500.00
                },
                {
                    "description": "NVMe storage upgrade kit",
                    "qty": 4,
                    "unit_price": 800.00
                },
            ],
            "total":
            12200.00,
            "status":
            "open",
            "created_at":
            "2026-05-11T10:00:00Z",
            "approved_by":
            None,
            "department":
            "Engineering/SRE",
        },
        {
            "po_id":
            "PO-1003",
            "requester":
            _user_obj("bob_m"),
            "vendor":
            "CloudRack Inc.",
            "items": [
                {
                    "description": "Database server (32-core, 128GB)",
                    "qty": 3,
                    "unit_price": 15000.00
                },
            ],
            "total":
            45000.00,
            "status":
            "open",
            "created_at":
            "2026-05-14T08:00:00Z",
            "approved_by":
            None,
            "department":
            "Engineering/SRE",
        },
        {
            "po_id":
            "PO-1004",
            "requester":
            _user_obj("jennifer"),
            "vendor":
            "NetGuard Solutions",
            "items": [
                {
                    "description": "Penetration testing engagement",
                    "qty": 1,
                    "unit_price": 25000.00
                },
            ],
            "total":
            25000.00,
            "status":
            "open",
            "created_at":
            "2026-05-13T14:00:00Z",
            "approved_by":
            None,
            "department":
            "Legal/Compliance",
        },
    ]
    approved_pos = [
        {
            "po_id":
            "PO-0991",
            "requester":
            _user_obj("anna"),
            "vendor":
            "DataFlow Systems",
            "items": [
                {
                    "description": "DataFlow Enterprise (annual)",
                    "qty": 1,
                    "unit_price": 36000.00
                },
            ],
            "total":
            36000.00,
            "status":
            "approved",
            "created_at":
            "2026-04-15T09:00:00Z",
            "approved_by":
            _user_obj("rachel"),
            "department":
            "Engineering/SRE",
        },
        {
            "po_id":
            "PO-0992",
            "requester":
            _user_obj("priya"),
            "vendor":
            "CloudRack Inc.",
            "items": [
                {
                    "description": "Laptop refresh (MBP M4) batch",
                    "qty": 10,
                    "unit_price": 2800.00
                },
            ],
            "total":
            28000.00,
            "status":
            "approved",
            "created_at":
            "2026-04-20T10:00:00Z",
            "approved_by":
            _user_obj("rachel"),
            "department":
            "IT",
        },
        {
            "po_id":
            "PO-0993",
            "requester":
            _user_obj("maya"),
            "vendor":
            "SecureSign Corp",
            "items": [
                {
                    "description": "Customer portal SSL certificates",
                    "qty": 5,
                    "unit_price": 200.00
                },
            ],
            "total":
            1000.00,
            "status":
            "approved",
            "created_at":
            "2026-05-01T09:00:00Z",
            "approved_by":
            _user_obj("rachel"),
            "department":
            "Customer Support",
        },
    ]
    received_pos = [
        {
            "po_id":
            "PO-0981",
            "requester":
            _user_obj("sam"),
            "vendor":
            "CloudRack Inc.",
            "items": [
                {
                    "description": "Network switch upgrade",
                    "qty": 2,
                    "unit_price": 3500.00
                },
            ],
            "total":
            7000.00,
            "status":
            "received",
            "created_at":
            "2026-03-15T09:00:00Z",
            "approved_by":
            _user_obj("rachel"),
            "department":
            "IT",
        },
        {
            "po_id":
            "PO-0982",
            "requester":
            _user_obj("bob_m"),
            "vendor":
            "DataFlow Systems",
            "items": [
                {
                    "description": "Log aggregation appliance",
                    "qty": 1,
                    "unit_price": 15000.00
                },
            ],
            "total":
            15000.00,
            "status":
            "received",
            "created_at":
            "2026-03-20T10:00:00Z",
            "approved_by":
            _user_obj("rachel"),
            "department":
            "Engineering/SRE",
        },
    ]

    for po in open_pos:
        (fin_root / "purchase_orders" / "open" /
         f"{po['po_id']}.json").write_text(json.dumps(po, indent=2) + "\n")
    for po in approved_pos:
        (fin_root / "purchase_orders" / "approved" /
         f"{po['po_id']}.json").write_text(json.dumps(po, indent=2) + "\n")
    for po in received_pos:
        (fin_root / "purchase_orders" / "received" /
         f"{po['po_id']}.json").write_text(json.dumps(po, indent=2) + "\n")

    pending_invoices = [
        {
            "invoice_id": "INV-3001",
            "vendor": "NorthHill Corp (self - customer billing)",
            "amount": 24000.00,
            "due_date": "2026-05-30",
            "po_reference": None,
            "status": "pending",
            "department": "Customer Support",
            "customer": "TechFlow (ACCT-1003)",
        },
        {
            "invoice_id": "INV-3002",
            "vendor": "CloudRack Inc.",
            "amount": 28000.00,
            "due_date": "2026-05-20",
            "po_reference": "PO-0992",
            "status": "pending",
            "department": "IT",
        },
        {
            "invoice_id": "INV-3003",
            "vendor": "DataFlow Systems",
            "amount": 36000.00,
            "due_date": "2026-05-25",
            "po_reference": "PO-0991",
            "status": "pending",
            "department": "Engineering/SRE",
        },
        {
            "invoice_id": "INV-3004",
            "vendor": "NetGuard Solutions",
            "amount": 5000.00,
            "due_date": "2026-06-01",
            "po_reference": None,
            "status": "pending",
            "department": "Legal/Compliance",
        },
        {
            "invoice_id": "INV-3005",
            "vendor": "SecureSign Corp",
            "amount": 1000.00,
            "due_date": "2026-05-31",
            "po_reference": "PO-0993",
            "status": "pending",
            "department": "Customer Support",
        },
    ]
    paid_invoices = [
        {
            "invoice_id": "INV-2991",
            "vendor": "CloudRack Inc.",
            "amount": 7000.00,
            "due_date": "2026-04-15",
            "po_reference": "PO-0981",
            "status": "paid",
            "department": "IT",
        },
        {
            "invoice_id": "INV-2992",
            "vendor": "DataFlow Systems",
            "amount": 15000.00,
            "due_date": "2026-04-20",
            "po_reference": "PO-0982",
            "status": "paid",
            "department": "Engineering/SRE",
        },
        {
            "invoice_id": "INV-2993",
            "vendor": "SecureSign Corp",
            "amount": 8000.00,
            "due_date": "2026-04-30",
            "po_reference": None,
            "status": "paid",
            "department": "IT",
        },
    ]
    disputed_invoices = [
        {
            "invoice_id":
            "INV-3006",
            "vendor":
            "NetGuard Solutions",
            "amount":
            12500.00,
            "due_date":
            "2026-05-15",
            "po_reference":
            None,
            "status":
            "disputed",
            "department":
            "Legal/Compliance",
            "dispute_reason":
            "Invoice for services not yet rendered. "
            "Penetration test (PO-1004) has not been "
            "approved yet.",
        },
    ]

    for inv in pending_invoices:
        (fin_root / "invoices" / "pending" / f"{inv['invoice_id']}.json"
         ).write_text(json.dumps(inv, indent=2) + "\n")
    for inv in paid_invoices:
        (fin_root / "invoices" / "paid" / f"{inv['invoice_id']}.json"
         ).write_text(json.dumps(inv, indent=2) + "\n")
    for inv in disputed_invoices:
        (fin_root / "invoices" / "disputed" / f"{inv['invoice_id']}.json"
         ).write_text(json.dumps(inv, indent=2) + "\n")

    q2_budget = {
        "fiscal_quarter":
        "Q2-2026",
        "period": {
            "start": "2026-04-01",
            "end": "2026-06-30"
        },
        "total_budget":
        1515000.00,
        "total_spent":
        1216900.00,
        "total_remaining":
        298100.00,
        "departments": [
            {
                "name": "Platform Engineering",
                "budget": 420000.00,
                "spent": 327600.00,
                "remaining": 92400.00,
                "status": "on_track",
            },
            {
                "name": "IT",
                "budget": 180000.00,
                "spent": 142200.00,
                "remaining": 37800.00,
                "status": "on_track",
            },
            {
                "name": "People/HR",
                "budget": 95000.00,
                "spent": 68400.00,
                "remaining": 26600.00,
                "status": "on_track",
            },
            {
                "name": "Finance",
                "budget": 65000.00,
                "spent": 41300.00,
                "remaining": 23700.00,
                "status": "on_track",
            },
            {
                "name": "Customer Support",
                "budget": 210000.00,
                "spent": 178500.00,
                "remaining": 31500.00,
                "status": "at_risk",
            },
            {
                "name": "Engineering/SRE",
                "budget": 350000.00,
                "spent": 298200.00,
                "remaining": 51800.00,
                "status": "on_track",
            },
            {
                "name": "Legal/Compliance",
                "budget": 120000.00,
                "spent": 108600.00,
                "remaining": 11400.00,
                "status": "over_budget",
            },
            {
                "name": "Executive",
                "budget": 75000.00,
                "spent": 52100.00,
                "remaining": 22900.00,
                "status": "on_track",
            },
        ],
    }
    (fin_root / "budgets" /
     "Q2_2026.json").write_text(json.dumps(q2_budget, indent=2) + "\n")


def write_customers(
    root: Path,
    extra_customers: list[dict] | None = None,
) -> list[dict]:
    """Materialize customer accounts and escalations on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
        extra_customers (list[dict] | None): Generated customers to append.

    Returns:
        list[dict]: All customer accounts (hand-crafted + generated).
    """
    cust_root = root / "customers"
    if cust_root.exists():
        shutil.rmtree(cust_root)
    (cust_root / "accounts").mkdir(parents=True, exist_ok=True)
    (cust_root / "escalations").mkdir(parents=True, exist_ok=True)

    accounts = [
        {
            "account_id":
            "ACCT-1001",
            "company_name":
            "GlobalTech",
            "tier":
            "enterprise",
            "arr":
            480000.00,
            "health_score":
            45,
            "csm":
            _user_obj("emily"),
            "renewal_date":
            "2026-08-15",
            "contacts": [
                {
                    "name": "Sarah Miller",
                    "email": "s.miller@globaltech.com",
                    "role": "VP Engineering"
                },
                {
                    "name": "James Park",
                    "email": "j.park@globaltech.com",
                    "role": "IT Director"
                },
            ],
            "products": ["platform-api", "auth-service", "analytics"],
        },
        {
            "account_id":
            "ACCT-1002",
            "company_name":
            "PayRight",
            "tier":
            "pro",
            "arr":
            96000.00,
            "health_score":
            72,
            "csm":
            _user_obj("emily"),
            "renewal_date":
            "2026-11-01",
            "contacts": [
                {
                    "name": "Linda Tran",
                    "email": "l.tran@payright.io",
                    "role": "CTO"
                },
            ],
            "products": ["platform-api", "webhooks"],
        },
        {
            "account_id":
            "ACCT-1003",
            "company_name":
            "TechFlow",
            "tier":
            "enterprise",
            "arr":
            360000.00,
            "health_score":
            88,
            "csm":
            _user_obj("emily"),
            "renewal_date":
            "2026-09-30",
            "contacts": [
                {
                    "name": "Mike Chen",
                    "email": "m.chen@techflow.dev",
                    "role": "Head of Product"
                },
                {
                    "name": "Amy Nakamura",
                    "email": "a.nakamura@techflow.dev",
                    "role": "Engineering Lead"
                },
            ],
            "products": ["platform-api", "analytics", "auth-service"],
        },
        {
            "account_id":
            "ACCT-1004",
            "company_name":
            "NovaCorp",
            "tier":
            "starter",
            "arr":
            12000.00,
            "health_score":
            95,
            "csm":
            _user_obj("carlos"),
            "renewal_date":
            "2027-01-15",
            "contacts": [
                {
                    "name": "Ryan Foster",
                    "email": "r.foster@novacorp.io",
                    "role": "Developer"
                },
            ],
            "products": ["platform-api"],
        },
        {
            "account_id":
            "ACCT-1005",
            "company_name":
            "DataVault",
            "tier":
            "pro",
            "arr":
            72000.00,
            "health_score":
            60,
            "csm":
            _user_obj("emily"),
            "renewal_date":
            "2026-12-01",
            "contacts": [
                {
                    "name": "Klaus Weber",
                    "email": "k.weber@datavault.eu",
                    "role": "DPO"
                },
                {
                    "name": "Anna Hoffmann",
                    "email": "a.hoffmann@datavault.eu",
                    "role": "CTO"
                },
            ],
            "products": ["platform-api", "analytics"],
        },
        {
            "account_id":
            "ACCT-1006",
            "company_name":
            "CloudBase",
            "tier":
            "enterprise",
            "arr":
            240000.00,
            "health_score":
            82,
            "csm":
            _user_obj("emily"),
            "renewal_date":
            "2026-10-15",
            "contacts": [
                {
                    "name": "Jennifer Adams",
                    "email": "j.adams@cloudbase.com",
                    "role": "VP Partnerships"
                },
            ],
            "products": ["platform-api", "auth-service"],
        },
    ]
    if extra_customers:
        gen_employees = generate_employees(seed=42)
        all_u = USERS + gen_employees
        for gen_cust in extra_customers:
            csm_handle = gen_cust.get("csm")
            if isinstance(csm_handle, str):
                match = next((u for u in all_u if u["handle"] == csm_handle),
                             None)
                if match:
                    gen_cust["csm"] = {
                        "id": match["id"],
                        "name": match["name"],
                        "email": match["email"],
                    }
                else:
                    gen_cust["csm"] = {
                        "id": "U000",
                        "name": csm_handle,
                        "email": f"{csm_handle}@northhill.com",
                    }
        accounts.extend(extra_customers)

    for acct in accounts:
        (cust_root / "accounts" / f"{acct['account_id']}.json"
         ).write_text(json.dumps(acct, indent=2) + "\n")

    escalations = [
        {
            "escalation_id":
            "ESC-1001",
            "account_id":
            "ACCT-1001",
            "severity":
            "high",
            "description":
            "GlobalTech experiencing login failures due to "
            "payments-api incident INC-5521. Account health "
            "dropped to 45. Renewal in 3 months.",
            "linked_ticket":
            "CS-1001",
            "linked_incidents": ["INC-5521"],
            "created_at":
            "2026-05-15T14:20:00Z",
            "status":
            "active",
            "owner":
            _user_obj("emily"),
        },
        {
            "escalation_id": "ESC-1002",
            "account_id": "ACCT-1002",
            "severity": "medium",
            "description": "PayRight webhook delivery delays affecting their "
            "real-time integration. CS-1003 in progress.",
            "linked_ticket": "CS-1003",
            "linked_incidents": [],
            "created_at": "2026-05-14T15:00:00Z",
            "status": "active",
            "owner": _user_obj("carlos"),
        },
        {
            "escalation_id":
            "ESC-1003",
            "account_id":
            "ACCT-1005",
            "severity":
            "high",
            "description":
            "DataVault submitted GDPR Article 17 data "
            "deletion request. Legal ticket LGL-1003 tracking. "
            "30-day compliance deadline from 2026-05-14.",
            "linked_ticket":
            "LGL-1003",
            "linked_incidents": [],
            "created_at":
            "2026-05-14T09:00:00Z",
            "status":
            "active",
            "owner":
            _user_obj("jennifer"),
        },
    ]
    for esc in escalations:
        (cust_root / "escalations" / f"{esc['escalation_id']}.json"
         ).write_text(json.dumps(esc, indent=2) + "\n")

    return accounts


def write_compliance(root: Path) -> None:
    """Materialize compliance data (contracts, audits, policies) on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    comp_root = root / "compliance"
    if comp_root.exists():
        shutil.rmtree(comp_root)
    for sub in ("contracts/in_review", "contracts/active", "contracts/expired",
                "audits", "policies"):
        (comp_root / sub).mkdir(parents=True, exist_ok=True)

    in_review_contracts = [
        {
            "contract_id":
            "CTR-1007",
            "counterparty":
            "CloudBase",
            "type":
            "NDA",
            "value":
            0,
            "start_date":
            "2026-05-20",
            "end_date":
            "2028-05-20",
            "status":
            "in_review",
            "owner":
            _user_obj("michael"),
            "review_notes":
            "Standard mutual NDA. CloudBase proposing "
            "partnership. Pending legal review.",
        },
        {
            "contract_id":
            "CTR-1008",
            "counterparty":
            "NetGuard Solutions",
            "type":
            "SOW",
            "value":
            25000.00,
            "start_date":
            "2026-06-01",
            "end_date":
            "2026-06-30",
            "status":
            "in_review",
            "owner":
            _user_obj("michael"),
            "review_notes":
            "Penetration testing engagement. Linked to "
            "PO-1004. Need to verify insurance and "
            "liability terms.",
        },
        {
            "contract_id":
            "CTR-1009",
            "counterparty":
            "DataVault",
            "type":
            "DPA",
            "value":
            0,
            "start_date":
            "2026-05-15",
            "end_date":
            "2027-05-15",
            "status":
            "in_review",
            "owner":
            _user_obj("jennifer"),
            "review_notes":
            "Data Processing Agreement update required "
            "following GDPR deletion request (LGL-1003).",
        },
    ]
    active_contracts = [
        {
            "contract_id":
            "CTR-1001",
            "counterparty":
            "GlobalTech",
            "type":
            "MSA",
            "value":
            480000.00,
            "start_date":
            "2025-08-15",
            "end_date":
            "2026-08-15",
            "status":
            "active",
            "owner":
            _user_obj("michael"),
            "review_notes":
            "Enterprise MSA. Auto-renews unless 60-day "
            "notice. Health score at 45 - retention risk.",
        },
        {
            "contract_id": "CTR-1002",
            "counterparty": "PayRight",
            "type": "MSA",
            "value": 96000.00,
            "start_date": "2025-11-01",
            "end_date": "2026-11-01",
            "status": "active",
            "owner": _user_obj("michael"),
            "review_notes": "",
        },
        {
            "contract_id": "CTR-1003",
            "counterparty": "CloudRack Inc.",
            "type": "MSA",
            "value": 250000.00,
            "start_date": "2025-01-01",
            "end_date": "2027-01-01",
            "status": "active",
            "owner": _user_obj("michael"),
            "review_notes": "Infrastructure vendor. Multi-year agreement.",
        },
        {
            "contract_id": "CTR-1004",
            "counterparty": "TechFlow",
            "type": "MSA",
            "value": 360000.00,
            "start_date": "2025-09-30",
            "end_date": "2026-09-30",
            "status": "active",
            "owner": _user_obj("michael"),
            "review_notes": "Enterprise MSA. 120 seat contract.",
        },
    ]
    expired_contracts = [
        {
            "contract_id": "CTR-0995",
            "counterparty": "OldVendor LLC",
            "type": "SOW",
            "value": 15000.00,
            "start_date": "2025-06-01",
            "end_date": "2026-03-31",
            "status": "expired",
            "owner": _user_obj("michael"),
            "review_notes": "Did not renew. Migrated to DataFlow Systems.",
        },
    ]

    for ctr in in_review_contracts:
        (comp_root / "contracts" / "in_review" / f"{ctr['contract_id']}.json"
         ).write_text(json.dumps(ctr, indent=2) + "\n")
    for ctr in active_contracts:
        (comp_root / "contracts" / "active" / f"{ctr['contract_id']}.json"
         ).write_text(json.dumps(ctr, indent=2) + "\n")
    for ctr in expired_contracts:
        (comp_root / "contracts" / "expired" / f"{ctr['contract_id']}.json"
         ).write_text(json.dumps(ctr, indent=2) + "\n")

    audits = [
        {
            "audit_id":
            "AUDIT-2026-SOC2",
            "framework":
            "SOC2",
            "status":
            "in_progress",
            "due_date":
            "2026-06-30",
            "started_at":
            "2026-04-01",
            "auditor":
            "Deloitte",
            "checklist": [
                {
                    "name": "Access Control Policy",
                    "status": "complete",
                    "owner": _user_obj("sam"),
                    "evidence_link": "/compliance/policies/POL-1001.json"
                },
                {
                    "name": "Change Management",
                    "status": "in_progress",
                    "owner": _user_obj("david"),
                    "evidence_link": None
                },
                {
                    "name": "Incident Response Plan",
                    "status": "complete",
                    "owner": _user_obj("bob_m"),
                    "evidence_link": "/compliance/policies/POL-1003.json"
                },
                {
                    "name": "Data Encryption at Rest",
                    "status": "complete",
                    "owner": _user_obj("anna"),
                    "evidence_link": "/gdocs/owned/encryption_policy.gdoc.json"
                },
                {
                    "name": "Employee Background Checks",
                    "status": "pending",
                    "owner": _user_obj("lisa"),
                    "evidence_link": None
                },
                {
                    "name": "Vendor Risk Assessment",
                    "status": "in_progress",
                    "owner": _user_obj("jennifer"),
                    "evidence_link": None
                },
                {
                    "name": "Network Security Controls",
                    "status": "complete",
                    "owner": _user_obj("derek"),
                    "evidence_link": "/compliance/policies/POL-1002.json"
                },
                {
                    "name": "Backup and Recovery",
                    "status": "complete",
                    "owner": _user_obj("bob_m"),
                    "evidence_link": None
                },
                {
                    "name": "Logical Access Reviews",
                    "status": "complete",
                    "owner": _user_obj("sam"),
                    "evidence_link": "/sheets/owned/Access_Matrix__SH103.json"
                },
                {
                    "name": "Security Awareness Training",
                    "status": "complete",
                    "owner": _user_obj("diana"),
                    "evidence_link": None
                },
                {
                    "name": "Password Policy Enforcement",
                    "status": "complete",
                    "owner": _user_obj("derek"),
                    "evidence_link": None
                },
                {
                    "name": "Vulnerability Management",
                    "status": "in_progress",
                    "owner": _user_obj("derek"),
                    "evidence_link": None
                },
                {
                    "name": "Physical Security",
                    "status": "pending",
                    "owner": _user_obj("sam"),
                    "evidence_link": None
                },
                {
                    "name": "Data Classification",
                    "status": "pending",
                    "owner": _user_obj("jennifer"),
                    "evidence_link": None
                },
                {
                    "name": "Business Continuity Plan",
                    "status": "in_progress",
                    "owner": _user_obj("robert"),
                    "evidence_link": None
                },
                {
                    "name": "Risk Assessment Process",
                    "status": "complete",
                    "owner": _user_obj("jennifer"),
                    "evidence_link": None
                },
                {
                    "name": "System Monitoring",
                    "status": "complete",
                    "owner": _user_obj("iris"),
                    "evidence_link": None
                },
                {
                    "name": "Secure SDLC",
                    "status": "in_progress",
                    "owner": _user_obj("anna"),
                    "evidence_link": None
                },
                {
                    "name": "API Security",
                    "status": "pending",
                    "owner": _user_obj("frank"),
                    "evidence_link": None
                },
                {
                    "name": "Logging and Audit Trail",
                    "status": "complete",
                    "owner": _user_obj("bob_m"),
                    "evidence_link": None
                },
                {
                    "name": "Third Party Integrations",
                    "status": "pending",
                    "owner": _user_obj("jennifer"),
                    "evidence_link": None
                },
                {
                    "name": "Data Retention Policy",
                    "status": "pending",
                    "owner": _user_obj("jennifer"),
                    "evidence_link": None
                },
                {
                    "name": "Endpoint Protection",
                    "status": "in_progress",
                    "owner": _user_obj("derek"),
                    "evidence_link": None
                },
                {
                    "name": "Disaster Recovery Testing",
                    "status": "pending",
                    "owner": _user_obj("bob_m"),
                    "evidence_link": None
                },
            ],
        },
        {
            "audit_id":
            "AUDIT-2026-GDPR",
            "framework":
            "GDPR",
            "status":
            "pending",
            "due_date":
            "2026-09-30",
            "started_at":
            None,
            "auditor":
            "TBD",
            "checklist": [
                {
                    "name": "Data Processing Inventory",
                    "status": "pending",
                    "owner": _user_obj("jennifer"),
                    "evidence_link": None
                },
                {
                    "name": "Consent Management",
                    "status": "pending",
                    "owner": _user_obj("jennifer"),
                    "evidence_link": None
                },
                {
                    "name": "Data Subject Rights Process",
                    "status": "pending",
                    "owner": _user_obj("michael"),
                    "evidence_link": None
                },
                {
                    "name": "Cross-Border Transfer Mechanisms",
                    "status": "pending",
                    "owner": _user_obj("michael"),
                    "evidence_link": None
                },
                {
                    "name": "Breach Notification Process",
                    "status": "pending",
                    "owner": _user_obj("jennifer"),
                    "evidence_link": None
                },
                {
                    "name": "DPA Review",
                    "status": "pending",
                    "owner": _user_obj("michael"),
                    "evidence_link": None
                },
            ],
        },
    ]
    for audit in audits:
        (comp_root / "audits" / f"{audit['audit_id']}.json"
         ).write_text(json.dumps(audit, indent=2) + "\n")

    all_user_ids = [u["id"] for u in USERS]
    acked_users = all_user_ids[:18]
    not_acked_users = all_user_ids[18:]

    policies = [
        {
            "policy_id":
            "POL-1001",
            "title":
            "Data Handling and Classification Policy",
            "version":
            "2.1",
            "effective_date":
            "2026-01-15",
            "acknowledgments": [{
                "user_id": uid,
                "acked_at": "2026-01-20T10:00:00Z"
            } for uid in acked_users] + [{
                "user_id": uid,
                "acked_at": None
            } for uid in not_acked_users],
        },
        {
            "policy_id":
            "POL-1002",
            "title":
            "Acceptable Use Policy",
            "version":
            "3.0",
            "effective_date":
            "2026-02-01",
            "acknowledgments": [{
                "user_id": uid,
                "acked_at": "2026-02-05T10:00:00Z"
            } for uid in acked_users[:20]] + [{
                "user_id": uid,
                "acked_at": None
            } for uid in all_user_ids[20:]],
        },
        {
            "policy_id":
            "POL-1003",
            "title":
            "Incident Response Policy",
            "version":
            "1.5",
            "effective_date":
            "2026-03-01",
            "acknowledgments": [{
                "user_id": uid,
                "acked_at": "2026-03-05T10:00:00Z"
            } for uid in acked_users[:15]] + [{
                "user_id": uid,
                "acked_at": None
            } for uid in all_user_ids[15:]],
        },
    ]
    for pol in policies:
        (comp_root / "policies" / f"{pol['policy_id']}.json"
         ).write_text(json.dumps(pol, indent=2) + "\n")


def write_engineering(root: Path) -> None:
    """Materialize GitHub, PagerDuty, and Datadog data on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    gh_root = root / "github"
    if gh_root.exists():
        shutil.rmtree(gh_root)
    repo = gh_root / "repos" / "northhill" / "platform-api"
    for sub in ("deployments", "commits", "pulls"):
        (repo / sub).mkdir(parents=True, exist_ok=True)

    deployments = [
        {
            "id":
            "d4e5f6",
            "environment":
            "production",
            "ref":
            "main",
            "sha":
            "f3a1b2c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4",
            "description":
            "Deploy platform-api v3.18.7",
            "creator": {
                "login": "frank.osei"
            },
            "created_at":
            "2026-05-15T13:55:00Z",
            "updated_at":
            "2026-05-15T13:59:00Z",
            "statuses": [
                {
                    "state": "success",
                    "created_at": "2026-05-15T13:59:00Z"
                },
            ],
        },
        {
            "id":
            "c3d4e5",
            "environment":
            "production",
            "ref":
            "main",
            "sha":
            "7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e",
            "description":
            "Deploy platform-api v3.18.6",
            "creator": {
                "login": "nina.gupta"
            },
            "created_at":
            "2026-05-14T10:30:00Z",
            "updated_at":
            "2026-05-14T10:35:00Z",
            "statuses": [
                {
                    "state": "success",
                    "created_at": "2026-05-14T10:35:00Z"
                },
            ],
        },
        {
            "id":
            "b2c3d4",
            "environment":
            "production",
            "ref":
            "main",
            "sha":
            "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b",
            "description":
            "Deploy platform-api v3.18.5",
            "creator": {
                "login": "david.park"
            },
            "created_at":
            "2026-05-13T09:00:00Z",
            "updated_at":
            "2026-05-13T09:05:00Z",
            "statuses": [
                {
                    "state": "success",
                    "created_at": "2026-05-13T09:05:00Z"
                },
            ],
        },
        {
            "id":
            "a1b2c3",
            "environment":
            "staging",
            "ref":
            "frank/optimize-pool",
            "sha":
            "f3a1b2c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4",
            "description":
            "Deploy platform-api v3.18.7-rc1 (staging)",
            "creator": {
                "login": "frank.osei"
            },
            "created_at":
            "2026-05-15T12:00:00Z",
            "updated_at":
            "2026-05-15T12:04:00Z",
            "statuses": [
                {
                    "state": "success",
                    "created_at": "2026-05-15T12:04:00Z"
                },
            ],
        },
    ]
    for d in deployments:
        (repo / "deployments" / f"{d['id']}.json").write_text(
            json.dumps(d, indent=2))

    critical_commit = {
        "sha":
        "f3a1b2c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4",
        "commit": {
            "author": {
                "name": "Frank Osei",
                "email": "frank.osei@northhill.com",
                "date": "2026-05-15T13:45:00Z",
            },
            "message": ("optimize connection pool settings\n\n"
                        "Reduce connection pool size to improve memory usage "
                        "per instance.\nAlso adjusted idle timeout for faster "
                        "connection recycling.\n\nRef: OPS-1247"),
        },
        "files": [{
            "filename":
            "config/database.go",
            "status":
            "modified",
            "additions":
            3,
            "deletions":
            3,
            "patch": ("@@ -42,9 +42,9 @@ func NewDatabaseConfig() "
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
        "stats": {
            "total": 6,
            "additions": 3,
            "deletions": 3
        },
    }
    (repo / "commits" / "f3a1b2c8.json").write_text(
        json.dumps(critical_commit, indent=2))

    previous_commit = {
        "sha":
        "7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e",
        "commit": {
            "author": {
                "name": "Nina Gupta",
                "email": "nina.gupta@northhill.com",
                "date": "2026-05-14T10:00:00Z",
            },
            "message":
            "add health check endpoint for platform-api\n\n"
            "Adds /healthz and /readyz endpoints with dependency "
            "checks for DB and Redis.",
        },
        "files": [{
            "filename": "handlers/health.go",
            "status": "added",
            "additions": 45,
            "deletions": 0,
        }],
        "stats": {
            "total": 45,
            "additions": 45,
            "deletions": 0
        },
    }
    (repo / "commits" / "7d8e9f0a.json").write_text(
        json.dumps(previous_commit, indent=2))

    pulls = [
        {
            "number":
            1847,
            "title":
            "optimize connection pool settings",
            "user": {
                "login": "frank.osei"
            },
            "state":
            "closed",
            "merged":
            True,
            "merged_at":
            "2026-05-15T13:50:00Z",
            "head": {
                "ref": "frank/optimize-pool",
                "sha": "f3a1b2c8"
            },
            "base": {
                "ref": "main"
            },
            "body":
            "Reduces connection pool to lower memory per pod. "
            "Benchmarked locally with 10 concurrent connections.\n\n"
            "Ref: OPS-1247",
            "labels": ["platform-api", "performance"],
        },
        {
            "number": 1845,
            "title": "add health check endpoints",
            "user": {
                "login": "nina.gupta"
            },
            "state": "open",
            "head": {
                "ref": "nina/healthcheck"
            },
            "base": {
                "ref": "main"
            },
            "body": "Adds /healthz and /readyz endpoints with dependency "
            "health checks.\n\nRef: OPS-1240",
            "labels": ["platform-api", "reliability"],
        },
    ]
    for pr in pulls:
        (repo / "pulls" / f"{pr['number']}.json").write_text(
            json.dumps(pr, indent=2))

    pd_root = root / "pagerduty"
    if pd_root.exists():
        shutil.rmtree(pd_root)
    (pd_root / "services").mkdir(parents=True, exist_ok=True)
    for status in ("triggered", "acknowledged", "resolved"):
        (pd_root / "incidents" / status).mkdir(parents=True, exist_ok=True)

    services = [
        {
            "id": "P001",
            "name": "platform-api",
            "description": "Core platform API service",
            "status": "critical",
            "escalation_policy": {
                "id": "EP001",
                "name": "Platform On-Call",
            },
        },
        {
            "id": "P002",
            "name": "auth-service",
            "description": "Authentication and authorization",
            "status": "active",
            "escalation_policy": {
                "id": "EP002",
                "name": "Identity On-Call",
            },
        },
    ]
    for svc in services:
        (pd_root / "services" / f"{svc['id']}.json").write_text(
            json.dumps(svc, indent=2))

    triggered_incidents = [
        {
            "id":
            "INC-5521",
            "incident_number":
            5521,
            "title":
            "P99 latency > 2000ms on platform-api "
            "/v1/payments/charge",
            "status":
            "triggered",
            "urgency":
            "high",
            "severity": {
                "value": "critical"
            },
            "service": {
                "id": "P001",
                "name": "platform-api"
            },
            "created_at":
            "2026-05-15T14:02:00Z",
            "updated_at":
            "2026-05-15T14:02:00Z",
            "assignments": [{
                "assignee": _user_obj("bob_m"),
            }],
            "acknowledgements": [{
                "at": "2026-05-15T14:03:30Z",
                "acknowledger": {
                    "id": "U212",
                    "name": "Bob Martinez",
                },
            }],
            "body": {
                "type":
                "incident_body",
                "details":
                ("Datadog monitor 'platform-api P99 latency' triggered.\n"
                 "Current value: 2147ms\nThreshold: 500ms\n"
                 "Duration: > 2 minutes\n\n"
                 "Correlated deployment: d4e5f6 (platform-api v3.18.7)\n"
                 "Linked ticket: OPS-1247\n\n"
                 "Triggered alerts:\n"
                 "- P99 latency on /v1/payments/charge: 2147ms "
                 "(threshold: 500ms)\n"
                 "- Error rate on platform-api: 4.2% (threshold: 1%)\n\n"
                 "Customer impact: GlobalTech (ACCT-1001) login failures "
                 "reported (CS-1001)"),
            },
        },
    ]
    resolved_incidents = [
        {
            "id": "INC-5518",
            "incident_number": 5518,
            "title": "Okta SSO auth failures affecting Slack workspace",
            "status": "resolved",
            "urgency": "high",
            "severity": {
                "value": "critical"
            },
            "service": {
                "id": "P002",
                "name": "auth-service"
            },
            "created_at": "2026-04-22T09:14:00Z",
            "resolved_at": "2026-04-22T09:54:00Z",
            "assignments": [{
                "assignee": _user_obj("sam"),
            }],
        },
    ]
    for inc in triggered_incidents:
        (pd_root / "incidents" / "triggered" / f"{inc['id']}.json").write_text(
            json.dumps(inc, indent=2))
    for inc in resolved_incidents:
        (pd_root / "incidents" / "resolved" / f"{inc['id']}.json").write_text(
            json.dumps(inc, indent=2))

    dd_root = root / "datadog"
    if dd_root.exists():
        shutil.rmtree(dd_root)
    logs_dir = dd_root / "logs" / "platform-api"
    logs_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir = dd_root / "metrics" / "platform-api"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    log_entries = [
        {
            "timestamp": "2026-05-15T13:55:00Z",
            "service": "platform-api",
            "level": "INFO",
            "message": "payment processed successfully",
            "attributes": {
                "endpoint": "/v1/payments/charge",
                "latency_ms": 145,
            },
        },
        {
            "timestamp": "2026-05-15T13:58:00Z",
            "service": "platform-api",
            "level": "INFO",
            "message": "deployment started: v3.18.7 (sha: f3a1b2c8)",
            "attributes": {
                "version": "v3.18.7",
                "deployer": "frank.osei",
            },
        },
        {
            "timestamp": "2026-05-15T13:59:00Z",
            "service": "platform-api",
            "level": "INFO",
            "message": "deployment completed: v3.18.7. Health check passed.",
            "attributes": {
                "version": "v3.18.7",
                "duration_seconds": 255,
            },
        },
        {
            "timestamp": "2026-05-15T14:00:32Z",
            "service": "platform-api",
            "level": "ERROR",
            "message": "connection pool exhausted: all 10 connections in use, "
            "23 requests waiting",
            "attributes": {
                "host": "platform-api-7b4f9d-xk2m1",
                "pool_size": 10,
                "waiting": 23,
            },
        },
        {
            "timestamp": "2026-05-15T14:00:35Z",
            "service": "platform-api",
            "level": "ERROR",
            "message": "request timeout after 2000ms on /v1/payments/charge",
            "attributes": {
                "host": "platform-api-7b4f9d-np8q2",
                "endpoint": "/v1/payments/charge",
                "latency_ms": 2000,
            },
        },
        {
            "timestamp": "2026-05-15T14:00:38Z",
            "service": "platform-api",
            "level": "ERROR",
            "message": "connection pool exhausted: all 10 connections in use, "
            "47 requests waiting",
            "attributes": {
                "host": "platform-api-7b4f9d-np8q2",
                "pool_size": 10,
                "waiting": 47,
            },
        },
        {
            "timestamp": "2026-05-15T14:00:40Z",
            "service": "platform-api",
            "level": "ERROR",
            "message": "request timeout after 2000ms on /v1/payments/charge",
            "attributes": {
                "host": "platform-api-7b4f9d-xk2m1",
                "endpoint": "/v1/payments/charge",
                "latency_ms": 2000,
            },
        },
        {
            "timestamp": "2026-05-15T14:01:00Z",
            "service": "platform-api",
            "level": "ERROR",
            "message": "connection pool exhausted: all 10 connections in use, "
            "89 requests waiting",
            "attributes": {
                "host": "platform-api-7b4f9d-xk2m1",
                "pool_size": 10,
                "waiting": 89,
            },
        },
        {
            "timestamp": "2026-05-15T14:01:15Z",
            "service": "platform-api",
            "level": "ERROR",
            "message":
            "payment processing failed: database connection timeout",
            "attributes": {
                "host": "platform-api-7b4f9d-np8q2",
                "error_code": "DB_CONN_TIMEOUT",
            },
        },
    ]
    (logs_dir / "2026-05-15.jsonl").write_text("\n".join(
        json.dumps(e, ensure_ascii=False) for e in log_entries) + "\n")

    latency_p99 = {
        "metric":
        "platform_api.latency.p99",
        "unit":
        "milliseconds",
        "points": [
            ["2026-05-15T13:00:00Z", 189],
            ["2026-05-15T13:15:00Z", 195],
            ["2026-05-15T13:30:00Z", 192],
            ["2026-05-15T13:45:00Z", 201],
            ["2026-05-15T14:00:00Z", 2147],
            ["2026-05-15T14:15:00Z", 2389],
        ],
        "tags": ["service:platform-api", "endpoint:/v1/payments/charge"],
    }
    error_rate = {
        "metric":
        "platform_api.error_rate",
        "unit":
        "percent",
        "points": [
            ["2026-05-15T13:00:00Z", 0.3],
            ["2026-05-15T13:15:00Z", 0.2],
            ["2026-05-15T13:30:00Z", 0.3],
            ["2026-05-15T13:45:00Z", 0.2],
            ["2026-05-15T14:00:00Z", 4.2],
            ["2026-05-15T14:15:00Z", 5.1],
        ],
        "tags": ["service:platform-api"],
    }
    (metrics_dir / "p99_latency.json").write_text(
        json.dumps(latency_p99, indent=2))
    (metrics_dir / "error_rate.json").write_text(
        json.dumps(error_rate, indent=2))


def write_database(root: Path, all_accounts: list[dict]) -> None:
    """Materialize Postgres-like database tables on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
        all_accounts (list[dict]): All customer accounts for FK references.
    """
    fake = FakerClass()
    FakerClass.seed(42 + 500)
    rng = random.Random(42 + 500)

    db_root = root / "database" / "tables"
    if (root / "database").exists():
        shutil.rmtree(root / "database")

    account_ids = [a["account_id"] for a in all_accounts]
    account_tiers = {a["account_id"]: a["tier"] for a in all_accounts}

    _write_users_table(db_root, fake, rng, account_ids)
    _write_events_table(db_root, rng)
    _write_subscriptions_table(db_root, rng, all_accounts)
    _write_invoices_table(db_root, rng, account_ids, account_tiers)


def _write_users_table(
    db_root: Path,
    fake: FakerClass,
    rng: random.Random,
    account_ids: list[str],
) -> None:
    table_dir = db_root / "users"
    table_dir.mkdir(parents=True, exist_ok=True)

    schema = {
        "table":
        "users",
        "columns": [
            {
                "name": "user_id",
                "type": "varchar(36)",
                "nullable": False,
                "primary_key": True
            },
            {
                "name": "account_id",
                "type": "varchar(16)",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "email",
                "type": "varchar(255)",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "created_at",
                "type": "timestamptz",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "last_login",
                "type": "timestamptz",
                "nullable": True,
                "primary_key": False
            },
            {
                "name": "plan",
                "type": "varchar(32)",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "status",
                "type": "varchar(16)",
                "nullable": False,
                "primary_key": False
            },
        ],
        "foreign_keys": [
            {
                "column": "account_id",
                "references": "subscriptions.account_id"
            },
        ],
    }
    (table_dir / "schema.json").write_text(json.dumps(schema, indent=2))

    lines = []
    for i in range(500):
        acct = rng.choice(account_ids)
        created = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(
            days=rng.randint(0, 850))
        last_login = created + timedelta(days=rng.randint(1, 365),
                                         hours=rng.randint(0, 23))
        if last_login > datetime(2026, 5, 15, tzinfo=timezone.utc):
            last_login = datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc)
        row = {
            "user_id":
            f"usr_{i:05d}",
            "account_id":
            acct,
            "email":
            fake.email(),
            "created_at":
            created.isoformat(),
            "last_login":
            last_login.isoformat(),
            "plan":
            rng.choice(["free", "pro", "enterprise"]),
            "status":
            rng.choices(["active", "inactive", "suspended"],
                        weights=[0.8, 0.15, 0.05],
                        k=1)[0],
        }
        lines.append(json.dumps(row, ensure_ascii=False))
    (table_dir / "data.jsonl").write_text("\n".join(lines) + "\n")

    stats = {
        "table": "users",
        "row_count": 500,
        "size_bytes": len("\n".join(lines)),
        "last_updated": "2026-05-15T12:00:00Z",
    }
    (table_dir / "stats.json").write_text(json.dumps(stats, indent=2))


def _write_events_table(db_root: Path, rng: random.Random) -> None:
    table_dir = db_root / "events"
    table_dir.mkdir(parents=True, exist_ok=True)

    schema = {
        "table":
        "events",
        "columns": [
            {
                "name": "event_id",
                "type": "varchar(36)",
                "nullable": False,
                "primary_key": True
            },
            {
                "name": "user_id",
                "type": "varchar(36)",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "event_type",
                "type": "varchar(32)",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "timestamp",
                "type": "timestamptz",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "metadata_json",
                "type": "jsonb",
                "nullable": True,
                "primary_key": False
            },
        ],
        "foreign_keys": [
            {
                "column": "user_id",
                "references": "users.user_id"
            },
        ],
    }
    (table_dir / "schema.json").write_text(json.dumps(schema, indent=2))

    event_types = [
        "login", "api_call", "export", "error", "page_view", "settings_change",
        "webhook_trigger"
    ]
    event_weights = [0.25, 0.30, 0.05, 0.10, 0.15, 0.05, 0.10]
    lines = []
    for i in range(5000):
        uid = f"usr_{rng.randint(0, 499):05d}"
        etype = rng.choices(event_types, weights=event_weights, k=1)[0]
        ts = datetime(2026, 5, 1, tzinfo=timezone.utc) + timedelta(
            days=rng.randint(0, 14),
            hours=rng.randint(0, 23),
            minutes=rng.randint(0, 59),
            seconds=rng.randint(0, 59))
        meta = {}
        if etype == "api_call":
            meta = {
                "endpoint":
                rng.choice([
                    "/v1/users", "/v1/payments/charge", "/v1/webhooks",
                    "/v1/auth/token", "/v1/analytics/query"
                ])
            }
        elif etype == "error":
            meta = {
                "error_code":
                rng.choice([
                    "connection_pool_exhausted", "timeout", "rate_limited",
                    "auth_failed", "invalid_payload"
                ])
            }
        row = {
            "event_id": f"evt_{i:07d}",
            "user_id": uid,
            "event_type": etype,
            "timestamp": ts.isoformat(),
            "metadata_json": meta,
        }
        lines.append(json.dumps(row, ensure_ascii=False))
    (table_dir / "data.jsonl").write_text("\n".join(lines) + "\n")

    stats = {
        "table": "events",
        "row_count": 5000,
        "size_bytes": len("\n".join(lines)),
        "last_updated": "2026-05-15T14:30:00Z",
    }
    (table_dir / "stats.json").write_text(json.dumps(stats, indent=2))


def _write_subscriptions_table(
    db_root: Path,
    rng: random.Random,
    all_accounts: list[dict],
) -> None:
    table_dir = db_root / "subscriptions"
    table_dir.mkdir(parents=True, exist_ok=True)

    schema = {
        "table":
        "subscriptions",
        "columns": [
            {
                "name": "subscription_id",
                "type": "varchar(36)",
                "nullable": False,
                "primary_key": True
            },
            {
                "name": "account_id",
                "type": "varchar(16)",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "plan",
                "type": "varchar(32)",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "mrr",
                "type": "numeric(12,2)",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "start_date",
                "type": "date",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "renewal_date",
                "type": "date",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "status",
                "type": "varchar(16)",
                "nullable": False,
                "primary_key": False
            },
        ],
        "foreign_keys": [
            {
                "column": "account_id",
                "references": "customers.account_id"
            },
        ],
    }
    (table_dir / "schema.json").write_text(json.dumps(schema, indent=2))

    lines = []
    for i, acct in enumerate(all_accounts):
        plan_map = {
            "enterprise": "enterprise",
            "business": "business",
            "pro": "business",
            "starter": "starter"
        }
        plan = plan_map.get(acct["tier"], "starter")
        mrr = round(acct["arr"] / 12, 2)
        start = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(
            days=rng.randint(0, 500))
        status = rng.choices(["active", "churned", "trial"],
                             weights=[0.85, 0.10, 0.05],
                             k=1)[0]
        row = {
            "subscription_id": f"sub_{i:05d}",
            "account_id": acct["account_id"],
            "plan": plan,
            "mrr": mrr,
            "start_date": start.strftime("%Y-%m-%d"),
            "renewal_date": acct["renewal_date"],
            "status": status,
        }
        lines.append(json.dumps(row, ensure_ascii=False))
    (table_dir / "data.jsonl").write_text("\n".join(lines) + "\n")

    stats = {
        "table": "subscriptions",
        "row_count": len(all_accounts),
        "size_bytes": len("\n".join(lines)),
        "last_updated": "2026-05-15T12:00:00Z",
    }
    (table_dir / "stats.json").write_text(json.dumps(stats, indent=2))


def _write_invoices_table(
    db_root: Path,
    rng: random.Random,
    account_ids: list[str],
    account_tiers: dict[str, str],
) -> None:
    table_dir = db_root / "invoices"
    table_dir.mkdir(parents=True, exist_ok=True)

    schema = {
        "table":
        "invoices",
        "columns": [
            {
                "name": "invoice_id",
                "type": "varchar(36)",
                "nullable": False,
                "primary_key": True
            },
            {
                "name": "account_id",
                "type": "varchar(16)",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "amount",
                "type": "numeric(12,2)",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "status",
                "type": "varchar(16)",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "due_date",
                "type": "date",
                "nullable": False,
                "primary_key": False
            },
            {
                "name": "paid_date",
                "type": "date",
                "nullable": True,
                "primary_key": False
            },
        ],
        "foreign_keys": [
            {
                "column": "account_id",
                "references": "subscriptions.account_id"
            },
        ],
    }
    (table_dir / "schema.json").write_text(json.dumps(schema, indent=2))

    lines = []
    for i in range(200):
        acct = rng.choice(account_ids)
        tier = account_tiers.get(acct, "starter")
        amount_range = {
            "enterprise": (5000, 45000),
            "business": (2000, 18000),
            "pro": (2000, 18000),
            "starter": (500, 5000)
        }
        lo, hi = amount_range.get(tier, (500, 5000))
        amount = round(rng.uniform(lo, hi), 2)
        due = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(
            days=rng.randint(0, 200))
        status = rng.choices(["paid", "pending", "overdue"],
                             weights=[0.65, 0.25, 0.10],
                             k=1)[0]
        paid_date = None
        if status == "paid":
            paid_date = (
                due - timedelta(days=rng.randint(0, 10))).strftime("%Y-%m-%d")
        row = {
            "invoice_id": f"db_inv_{i:05d}",
            "account_id": acct,
            "amount": amount,
            "status": status,
            "due_date": due.strftime("%Y-%m-%d"),
            "paid_date": paid_date,
        }
        lines.append(json.dumps(row, ensure_ascii=False))
    (table_dir / "data.jsonl").write_text("\n".join(lines) + "\n")

    stats = {
        "table": "invoices",
        "row_count": 200,
        "size_bytes": len("\n".join(lines)),
        "last_updated": "2026-05-15T12:00:00Z",
    }
    (table_dir / "stats.json").write_text(json.dumps(stats, indent=2))


def write_s3(root: Path) -> None:
    """Materialize S3-like file storage on disk.

    Args:
        root (Path): Root directory for the synthetic workspace.
    """
    rng = random.Random(42 + 600)
    s3_root = root / "s3" / "northhill-data"
    if (root / "s3").exists():
        shutil.rmtree(root / "s3")

    _write_s3_logs(s3_root, rng)
    _write_s3_exports(s3_root)
    _write_s3_artifacts(s3_root)
    _write_s3_backups(s3_root)
    _write_s3_reports(s3_root)


def _write_s3_logs(s3_root: Path, rng: random.Random) -> None:
    log_services = ["platform-api"]
    normal_messages = [
        "Request processed successfully",
        "Cache hit for user session",
        "Webhook delivered to endpoint",
        "Authentication token refreshed",
        "Database query completed in {ms}ms",
        "Rate limit check passed",
        "Health check responded 200",
        "Background job completed",
        "API response served from cache",
        "Connection established to upstream service",
    ]
    warn_messages = [
        "Slow query detected: {ms}ms exceeds threshold",
        "Connection pool utilization at 85%",
        "Retry attempt 2/3 for webhook delivery",
        "Memory usage approaching soft limit",
        "Deprecated API version v1.2 called",
    ]
    error_messages = [
        "Connection pool exhausted — all connections in use",
        "Request timeout after 30000ms",
        "Authentication failed for service account",
        "Database connection refused",
        "Internal server error in payment processing",
    ]

    for svc in log_services:
        for day in range(10, 16):
            log_dir = s3_root / "logs" / svc / "2026" / "05" / f"{day:02d}"
            log_dir.mkdir(parents=True, exist_ok=True)

            lines = []
            is_incident_day = (day == 15)
            n_lines = rng.randint(80, 120)
            for li in range(n_lines):
                hour = rng.randint(6, 22)
                minute = rng.randint(0, 59)
                second = rng.randint(0, 59)
                ts = f"2026-05-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"

                if is_incident_day and 14 <= hour <= 15:
                    level = rng.choices(["ERROR", "WARN", "INFO"],
                                        weights=[0.5, 0.3, 0.2],
                                        k=1)[0]
                else:
                    level = rng.choices(["INFO", "WARN", "ERROR"],
                                        weights=[0.80, 0.12, 0.08],
                                        k=1)[0]

                if level == "INFO":
                    msg = rng.choice(normal_messages).format(
                        ms=rng.randint(5, 200))
                elif level == "WARN":
                    msg = rng.choice(warn_messages).format(
                        ms=rng.randint(500, 3000))
                else:
                    msg = rng.choice(error_messages)

                lines.append(f"{ts} {level} [{svc}] {msg}")

            lines.sort()
            (log_dir / "app.log").write_text("\n".join(lines) + "\n")


def _write_s3_exports(s3_root: Path) -> None:
    exports_dir = s3_root / "exports" / "monthly"
    exports_dir.mkdir(parents=True, exist_ok=True)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "account_id", "company_name", "tier", "arr", "health_score",
        "renewal_date"
    ])
    sample_customers = [
        ("ACCT-1001", "GlobalTech", "enterprise", 480000, 45, "2026-08-15"),
        ("ACCT-1002", "PayRight", "pro", 96000, 72, "2026-11-01"),
        ("ACCT-1003", "TechFlow", "enterprise", 360000, 88, "2026-09-30"),
        ("ACCT-1004", "NovaCorp", "starter", 12000, 95, "2027-01-15"),
        ("ACCT-1005", "DataVault", "pro", 72000, 60, "2026-12-01"),
        ("ACCT-1006", "CloudBase", "enterprise", 240000, 82, "2026-10-15"),
    ]
    for row in sample_customers:
        writer.writerow(row)
    (exports_dir / "2026-04-customers.csv").write_text(buf.getvalue())

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["month", "product", "revenue", "customers", "mrr"])
    revenue_data = [
        ("2026-04", "platform-api", 892000, 45, 74333),
        ("2026-04", "auth-service", 312000, 18, 26000),
        ("2026-04", "analytics", 196000, 12, 16333),
    ]
    for row in revenue_data:
        writer.writerow(row)
    (exports_dir / "2026-04-revenue.csv").write_text(buf.getvalue())


def _write_s3_artifacts(s3_root: Path) -> None:
    deploy_dir = s3_root / "artifacts" / "deployments" / "v3.18.7"
    deploy_dir.mkdir(parents=True, exist_ok=True)

    build_log_lines = [
        "[2026-05-15T13:45:00Z] BUILD START platform-api v3.18.7",
        "[2026-05-15T13:45:01Z] Triggered by: frank.osei",
        "[2026-05-15T13:45:01Z] Commit: f3a1b2c8",
        "[2026-05-15T13:45:01Z]   tune connection pool settings",
        "[2026-05-15T13:45:02Z] Branch: main (PR #1847)",
        "[2026-05-15T13:45:10Z] Step 1/6: Checkout ... OK",
        "[2026-05-15T13:45:25Z] Step 2/6: Dependencies OK (15s)",
        "[2026-05-15T13:45:55Z] Step 3/6: Tests OK (847 passed)",
        "[2026-05-15T13:46:10Z] Step 4/6: Build image OK (15s)",
        "[2026-05-15T13:46:15Z] Step 5/6: Push registry OK",
        "[2026-05-15T13:46:20Z] Step 6/6: Deploy to prod OK",
        "[2026-05-15T13:46:20Z] Deployment ID: d4e5f6",
        "[2026-05-15T13:46:20Z] Config changes detected:",
        "[2026-05-15T13:46:20Z]   connectionPoolSize: 50 -> 10",
        "[2026-05-15T13:46:20Z]   connectionTimeout: 30s (unchanged)",
        "[2026-05-15T13:46:25Z] Health check: PASSING (3/3)",
        "[2026-05-15T13:46:30Z] BUILD COMPLETE",
        "[2026-05-15T14:00:30Z] ALERT: Error rate spike 4.2%",
        "[2026-05-15T14:00:31Z] ALERT: P99 latency 2147ms",
    ]
    build_log = "\n".join(build_log_lines) + "\n"
    (deploy_dir / "build.log").write_text(build_log)


def _write_s3_backups(s3_root: Path) -> None:
    backup_dir = s3_root / "backups" / "db"
    backup_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "backup_id": "bkp-2026-05-14-001",
        "database": "platform_production",
        "timestamp": "2026-05-14T02:00:00Z",
        "size_bytes": 4_831_029_248,
        "format": "pg_dump_custom",
        "compression": "gzip",
        "tables": 47,
        "rows_total": 12_847_392,
        "checksum_sha256": "a3b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0",
        "retention_days": 30,
        "status": "completed",
    }
    (backup_dir / "2026-05-14-platform-db.sql.meta").write_text(
        json.dumps(meta, indent=2))


def _write_s3_reports(s3_root: Path) -> None:
    reports_dir = s3_root / "reports" / "quarterly"
    reports_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "report_id":
        "Q1-2026-board",
        "title":
        "Q1 2026 Board Deck",
        "format":
        "pdf",
        "pages":
        42,
        "created_by":
        "robert.singh@northhill.com",
        "created_at":
        "2026-04-05T10:00:00Z",
        "size_bytes":
        8_421_376,
        "sections": [
            "Executive Summary",
            "Revenue & ARR",
            "Customer Health",
            "Engineering Velocity",
            "Headcount & Hiring",
            "Q2 Outlook",
        ],
    }
    (reports_dir / "Q1-2026-board-deck.meta").write_text(
        json.dumps(meta, indent=2))


def main(root: str | Path = DEFAULT_ROOT, *, clean: bool = True) -> Path:
    """Seed the NorthHill Corp full enterprise corpus on disk.

    Args:
        root (str | Path): Destination directory for the synthetic workspace.
        clean (bool): If True (default), wipe the root before seeding.
    """
    target = Path(root).expanduser().resolve()
    if clean and target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    gen_employees = generate_employees(seed=42)
    support_handles = [
        u["handle"] for u in USERS
        if u["title"] in ("Support Lead", "Support Agent",
                          "Customer Success Manager")
    ]
    support_handles += [
        e["handle"] for e in gen_employees
        if e.get("team") == "Customer Support"
    ]
    gen_customers = generate_customers(support_handles, seed=42)
    gen_tickets = generate_support_tickets(gen_customers,
                                           support_handles,
                                           seed=42)
    ambient = generate_ambient_messages(USERS + gen_employees,
                                        CHANNELS,
                                        seed=42)

    write_slack(target, extra_users=gen_employees, ambient_messages=ambient)
    write_sheets(target)
    write_docs(target)
    write_tickets(target, extra_cs_tickets=gen_tickets)
    write_finance(target)
    all_accounts = write_customers(target, extra_customers=gen_customers)
    write_compliance(target)
    write_engineering(target)
    write_database(target, all_accounts)
    write_s3(target)
    return target


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the NorthHill Corp full enterprise corpus on disk.")
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
