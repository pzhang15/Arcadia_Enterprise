import argparse
import json
import shutil
from pathlib import Path

USERS = [
    {"id": "U001", "name": "pat", "real_name": "Pat Zhang", "title": "TPM, Platform"},
    {"id": "U002", "name": "sridhar", "real_name": "Sridhar Kumar", "title": "Director of Eng"},
    {"id": "U003", "name": "rachel", "real_name": "Rachel Chen", "title": "Eng Lead, Aurora"},
    {"id": "U004", "name": "james", "real_name": "James O'Brien", "title": "CS Lead"},
    {"id": "U005", "name": "diana", "real_name": "Diana Park", "title": "PM, Data"},
]

CHANNELS = [
    {"id": "C201", "name": "general"},
    {"id": "C202", "name": "eng-aurora"},
    {"id": "C203", "name": "eng-falcon"},
    {"id": "C204", "name": "cs-escalations"},
    {"id": "C205", "name": "incidents"},
    {"id": "C206", "name": "leadership"},
]

DMS = [
    {"id": "D101", "with_user_id": "U002"},
    {"id": "D102", "with_user_id": "U003"},
    {"id": "D103", "with_user_id": "U004"},
    {"id": "D104", "with_user_id": "U005"},
]

CHANNEL_MESSAGES = {
    "C202": [
        ("2026-05-05", "U003", "1715000000.000100",
         "blocker on aurora migration tool — getting 504s when trying to import the customer table from acme. "
         "anyone seen this in staging?"),
        ("2026-05-05", "U001", "1715000300.000100",
         "yeah I saw it once last week. think it's the chunked upload timing out for tables >2GB. "
         "looking into it now."),
        ("2026-05-06", "U001", "1715090000.000100",
         "PR up: helios/aurora#234 — switches to streaming uploads with resumable chunks. "
         "needs review."),
        ("2026-05-06", "U003", "1715094000.000100",
         "lgtm, merging. let's get it in tonight's beta build."),
        ("2026-05-07", "U004", "1715180000.000100",
         "FYI acme is going to retry their migration tonight. they're our reference for the GA pitch so "
         "let's babysit it."),
        ("2026-05-08", "U004", "1715268000.000100",
         "acme migration ran overnight. 99% rows landed, 12 row failures on the orders table. "
         "filing INC0012345 for tracking."),
        ("2026-05-08", "U001", "1715269000.000100",
         "good outcome. let's patch the row-level failures next sprint. owner: me."),
        ("2026-05-09", "U003", "1715354000.000100",
         "btw the streaming upload changes affect the falcon ingestion path too. "
         "we should sync next week before falcon RFC v3 goes final."),
    ],
    "C203": [
        ("2026-05-06", "U005", "1715094500.000100",
         "draft of falcon RFC v3 is up in gdocs/owned. main change: separate hot/cold storage tiers, "
         "borrow aurora's chunked-upload pattern. would love comments by friday."),
        ("2026-05-07", "U003", "1715180500.000100",
         "read v3. concern: tier transition logic is hand-wavy in §4. how do we decide when a partition "
         "moves from hot to cold? need a concrete policy."),
        ("2026-05-07", "U005", "1715181000.000100",
         "fair. I'll add a policy section. thinking: time-based default (>30 days) plus override per "
         "table. open question: do we let customers configure it?"),
        ("2026-05-08", "U001", "1715268500.000100",
         "+1 to letting customers configure. but default should be safe — last thing we want is "
         "a customer surprised by hot-tier billing."),
    ],
    "C204": [
        ("2026-05-07", "U004", "1715180300.000100",
         "P1: acme reporting data loss on aurora migration. 3 tables affected. incident bridge open."),
        ("2026-05-07", "U001", "1715180700.000100",
         "investigating. see #eng-aurora — I think it's the 504 issue. fix is in helios/aurora#234, "
         "rolling out to acme tonight."),
        ("2026-05-08", "U004", "1715268500.000100",
         "acme satisfied with hot-fix. closing P1. opened INC0012345 for the row-level failures as P3 "
         "follow-up. customer happy, GA pitch survived."),
    ],
    "C205": [
        ("2026-05-07", "U001", "1715180500.000100",
         "incident report: aurora 504s on large table imports. impact: acme migration, possibly others. "
         "mitigation: helios/aurora#234. ETA: tonight."),
        ("2026-05-08", "U001", "1715268700.000100",
         "incident resolved. write-up coming in /gdocs/owned (Aurora Beta Postmortem)."),
    ],
    "C206": [
        ("2026-05-05", "U002", "1714980000.000100",
         "leadership review this friday. each team prep a 5-min update with: shipped, blocked, asks. "
         "tracker is in /sheets/owned/ (Q2 Project Tracker)."),
        ("2026-05-08", "U002", "1715269500.000100",
         "good week for aurora. let's call out the acme save in friday's review."),
    ],
    "C201": [
        ("2026-05-06", "U002", "1715090500.000100",
         "all-hands recording posted. main beat: Q2 OKRs are tracking, customer health is improving, "
         "we're hiring 2 more SREs."),
    ],
}

DM_MESSAGES = {
    "D101": [  # with sridhar (manager)
        ("2026-05-05", "U002", "1714983000.000100",
         "hey can you give me an update on aurora ahead of leadership review fri? "
         "specifically the timeline question."),
        ("2026-05-05", "U001", "1714984000.000100",
         "sure — beta is out, hitting some scaling issues with bigger customers, "
         "working through them. timeline: GA mid-june if no surprises."),
        ("2026-05-08", "U002", "1715270000.000100",
         "saw the acme save. nice work. friday review still on?"),
        ("2026-05-08", "U001", "1715270500.000100",
         "yes. will prep slides today."),
        ("2026-05-09", "U002", "1715356000.000100",
         "also — I want to talk about your Q3 scope at our 1:1. "
         "thinking falcon could use a TPM, are you interested?"),
    ],
    "D102": [  # with rachel (eng lead)
        ("2026-05-06", "U003", "1715091000.000100",
         "thx for the quick fix on aurora. owe you a coffee."),
        ("2026-05-06", "U001", "1715091500.000100",
         "lol any time. one ask: when you have a sec, can you do a security review on "
         "helios/aurora#234? streaming uploads have a different threat surface."),
        ("2026-05-09", "U003", "1715357000.000100",
         "security review done — helios/aurora#234 looks clean. one nit posted."),
    ],
    "D103": [  # with james (CS lead)
        ("2026-05-07", "U004", "1715181500.000100",
         "thanks for jumping on acme today. I owe the customer a follow-up email — "
         "can I cite that the row-level fix is queued for next sprint?"),
        ("2026-05-07", "U001", "1715182000.000100",
         "yes. I'll own it personally. ETA: 2 weeks."),
        ("2026-05-09", "U004", "1715357500.000100",
         "acme exec asking when GA is. I told them mid-june, ok?"),
    ],
    "D104": [  # with diana (PM peer)
        ("2026-05-08", "U005", "1715269200.000100",
         "any feedback on falcon RFC v3 by friday would be huge."),
        ("2026-05-08", "U001", "1715269500.000100",
         "reading tonight. quick reaction: I love the tiering, worried about customer-config exposing "
         "billing surprises. will leave detailed comments in the doc."),
    ],
}


def slack_message(user_id: str, ts: str, text: str) -> dict:
    return {
        "type": "message",
        "user": user_id,
        "text": text,
        "ts": ts,
        "team": "T001",
    }


def write_slack(root: Path) -> None:
    slack_root = root / "slack"
    if slack_root.exists():
        shutil.rmtree(slack_root)
    for ch in CHANNELS:
        ch_dir = slack_root / "channels" / f"{ch['name']}__{ch['id']}"
        msgs_by_day: dict[str, list[dict]] = {}
        for date, user_id, ts, text in CHANNEL_MESSAGES.get(ch["id"], []):
            msgs_by_day.setdefault(date, []).append(slack_message(user_id, ts, text))
        for date, msgs in msgs_by_day.items():
            day_dir = ch_dir / date
            day_dir.mkdir(parents=True, exist_ok=True)
            (day_dir / "files").mkdir(exist_ok=True)
            (day_dir / "chat.jsonl").write_text(
                "\n".join(json.dumps(m, ensure_ascii=False) for m in msgs) + "\n")
        if not msgs_by_day:
            ch_dir.mkdir(parents=True, exist_ok=True)
    for dm in DMS:
        peer = next(u for u in USERS if u["id"] == dm["with_user_id"])
        dm_dir = slack_root / "dms" / f"{peer['name']}__{dm['id']}"
        msgs_by_day = {}
        for date, user_id, ts, text in DM_MESSAGES.get(dm["id"], []):
            msgs_by_day.setdefault(date, []).append(slack_message(user_id, ts, text))
        for date, msgs in msgs_by_day.items():
            day_dir = dm_dir / date
            day_dir.mkdir(parents=True, exist_ok=True)
            (day_dir / "files").mkdir(exist_ok=True)
            (day_dir / "chat.jsonl").write_text(
                "\n".join(json.dumps(m, ensure_ascii=False) for m in msgs) + "\n")
    users_dir = slack_root / "users"
    users_dir.mkdir(parents=True, exist_ok=True)
    for u in USERS:
        profile = {
            "id": u["id"],
            "name": u["name"],
            "real_name": u["real_name"],
            "profile": {"title": u["title"]},
        }
        (users_dir / f"{u['name']}__{u['id']}.json").write_text(
            json.dumps(profile, indent=2))


def cell(value) -> dict:
    return {
        "formattedValue": str(value),
        "userEnteredValue": {"stringValue": str(value)},
        "effectiveValue": {"stringValue": str(value)},
    }


def row(values: list) -> dict:
    return {"values": [cell(v) for v in values]}


def gsheet(spreadsheet_id: str, title: str, sheets: list[dict]) -> dict:
    return {
        "spreadsheetId": spreadsheet_id,
        "spreadsheetUrl": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
        "properties": {"title": title, "locale": "en_US", "timeZone": "America/Los_Angeles"},
        "sheets": sheets,
    }


def make_sheet_tab(sheet_id: int, title: str, rows: list[list]) -> dict:
    return {
        "properties": {
            "sheetId": sheet_id,
            "title": title,
            "index": sheet_id,
            "gridProperties": {"rowCount": max(len(rows), 100), "columnCount": 26},
        },
        "data": [{"rowData": [row(r) for r in rows]}],
    }


def write_sheets(root: Path) -> None:
    sheets_root = root / "sheets"
    if sheets_root.exists():
        shutil.rmtree(sheets_root)
    owned = sheets_root / "owned"
    shared = sheets_root / "shared"
    owned.mkdir(parents=True, exist_ok=True)
    shared.mkdir(parents=True, exist_ok=True)

    tracker_rows = [
        ["Project", "Owner", "Status", "Phase", "Last Update", "Slack Channel", "Notes"],
        ["Aurora", "pat", "in_progress", "Beta", "2026-05-09",
         "#eng-aurora",
         "Customer migration tool. Hit 504s on acme migration; hot-fix shipped (helios/aurora#234). "
         "Row-level failure follow-up queued. GA target mid-June."],
        ["Falcon", "rachel", "in_progress", "Design",
         "2026-05-08", "#eng-falcon",
         "Internal data platform. RFC v3 in review. Open question: customer-configurable tier policy."],
        ["Cobalt", "james", "done", "Maintenance",
         "2026-05-01", "#cs-escalations",
         "Released last quarter. No active incidents this week."],
        ["Stargate", "diana", "not_started", "Discovery",
         "2026-04-15", "",
         "Q3 candidate. Multi-tenant analytics. Spec doc TBD."],
    ]
    okr_rows = [
        ["Objective", "Key Result", "Owner", "Q2 Target", "Current", "Status"],
        ["Win the migration market", "5 reference customers in production", "pat", "5", "3", "on_track"],
        ["Win the migration market", "<2hr P95 migration time", "pat", "120min", "180min", "at_risk"],
        ["Ship Falcon GA", "RFC approved", "rachel", "Apr 30", "May 12 (slipped)", "at_risk"],
        ["Ship Falcon GA", "Beta with 3 customers", "rachel", "Jun 30", "0", "on_track"],
        ["Customer health > 8.0", "NPS rolling 30d", "james", "8.0", "7.6", "at_risk"],
    ]

    tracker = gsheet(
        "SH001",
        "Q2 Project Tracker",
        [make_sheet_tab(0, "Active", tracker_rows)],
    )
    okrs = gsheet(
        "SH002",
        "Q2 OKRs",
        [make_sheet_tab(0, "Tracking", okr_rows)],
    )

    (owned / "2026-05-09_Q2_Project_Tracker__SH001.gsheet.json").write_text(
        json.dumps(tracker, indent=2))
    (owned / "2026-05-08_Q2_OKRs__SH002.gsheet.json").write_text(
        json.dumps(okrs, indent=2))


def gdoc(doc_id: str, title: str, paragraphs: list[str]) -> dict:
    content = []
    for p in paragraphs:
        content.append({
            "paragraph": {
                "elements": [{"textRun": {"content": p + "\n", "textStyle": {}}}],
                "paragraphStyle": {},
            }
        })
    return {
        "documentId": doc_id,
        "title": title,
        "body": {"content": content},
        "documentStyle": {},
        "namedStyles": {},
        "revisionId": "rev-1",
        "suggestionsViewMode": "DEFAULT_FOR_CURRENT_ACCESS",
    }


def write_docs(root: Path) -> None:
    docs_root = root / "gdocs"
    if docs_root.exists():
        shutil.rmtree(docs_root)
    owned = docs_root / "owned"
    shared = docs_root / "shared"
    owned.mkdir(parents=True, exist_ok=True)
    shared.mkdir(parents=True, exist_ok=True)

    falcon_rfc = gdoc("GD001", "Falcon RFC v3", [
        "# Falcon RFC v3 — Hot/Cold Storage Tiers",
        "Author: Diana Park (PM, Data). Status: in review. Target merge: 2026-05-15.",
        "## §1 Background",
        "Falcon today stores all partitions in hot tier. Cost is dominated by partitions older than 30 days "
        "that are read <1x/month. We propose splitting into hot and cold tiers to cut storage cost ~60%.",
        "## §2 Design",
        "Two physical buckets: hot (SSD-backed, ms reads) and cold (object storage, sec reads). "
        "A scheduled job migrates partitions between tiers per policy.",
        "## §3 Lessons from Aurora",
        "Aurora's chunked-upload pattern (helios/aurora#234) handles partial-failure recovery cleanly. "
        "We borrow the same resumable-chunks approach for tier-transition jobs.",
        "## §4 Tier-transition policy (NEEDS POLICY)",
        "Default: partitions >30 days old since last read move to cold. "
        "Open question: do we let customers configure this? Pat raised the concern that customer-config "
        "could expose them to billing surprises if they accidentally pin everything to hot tier.",
        "## §5 Open Questions",
        "- Customer-configurable tier policy: yes/no, with what guardrails?",
        "- Re-promotion: if a cold partition is read 5x in a day, do we auto-promote back to hot?",
        "- Pricing impact: do we surface tier-cost in customer dashboard, or hide it?",
    ])

    aurora_pm = gdoc("GD002", "Aurora Beta Postmortem", [
        "# Aurora Beta Postmortem — 2026-05-08",
        "Author: Pat Zhang. Status: draft.",
        "## What happened",
        "On 2026-05-07, Acme attempted a production migration of their customer table (~3.2GB) "
        "and hit cascading 504 timeouts. Job partially completed; 3 destination tables had data loss.",
        "## Root cause",
        "Chunked-upload code path used a single non-resumable HTTP request per chunk. For chunks >800MB "
        "the upstream gateway timed out at 60s. Failures were not idempotent — retries duplicated rows.",
        "## Mitigation",
        "helios/aurora#234 switched to resumable streaming uploads with per-chunk acks. Acme retried "
        "successfully on 2026-05-08 with 12 row-level failures (separate issue, queued for next sprint).",
        "## Action items",
        "- [pat] File row-level-failure ticket. Owner: me. ETA: 2 weeks.",
        "- [rachel] Security review of streaming-upload threat surface. Done 2026-05-09.",
        "- [james] Update Acme reference quote for the GA deck.",
    ])

    one_on_one = gdoc("GD003", "1:1 Notes - Sridhar", [
        "# 1:1 with Sridhar — recurring weekly",
        "## 2026-05-09 agenda (next session)",
        "- Aurora: review the acme save, talk through GA timeline (mid-june if no surprises).",
        "- Falcon TPM ask — Sridhar floated me as TPM for falcon. Reaction: interested but want to "
        "  finish aurora GA first. Decision needed by end of May.",
        "- Q3 scope discussion.",
        "## 2026-05-02 (last session)",
        "- Discussed leadership review prep. Sridhar wants per-team 5-min updates with "
        "  shipped/blocked/asks framing.",
        "- Headcount: 2 SRE openings approved.",
    ])

    (owned / "2026-05-08_Falcon_RFC_v3__GD001.gdoc.json").write_text(
        json.dumps(falcon_rfc, indent=2))
    (owned / "2026-05-08_Aurora_Beta_Postmortem__GD002.gdoc.json").write_text(
        json.dumps(aurora_pm, indent=2))
    (owned / "2026-05-09_1on1_Notes_Sridhar__GD003.gdoc.json").write_text(
        json.dumps(one_on_one, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed a synthetic enterprise workspace on local disk.")
    parser.add_argument("--root", default="~/mirage-demo",
                        help="Where to create the synthetic tree (default ~/mirage-demo).")
    parser.add_argument("--clean", action="store_true",
                        help="Delete the entire root before seeding.")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    if args.clean and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    write_slack(root)
    write_sheets(root)
    write_docs(root)
    n_files = sum(1 for _ in root.rglob("*") if _.is_file())
    print(f"seeded {n_files} files into {root}")
    print("layout:")
    for p in sorted(root.iterdir()):
        print(f"  {p.name}/")


if __name__ == "__main__":
    main()
