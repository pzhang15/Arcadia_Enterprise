import json
from pathlib import Path

import pytest


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text())


def _gsheet_cells(p: Path) -> list[list[str]]:
    sheet = _read_json(p)
    rows = sheet["sheets"][0]["data"][0]["rowData"]
    return [
        [cell.get("formattedValue", "") for cell in row.get("values", [])]
        for row in rows
    ]


def test_inc_1001_references_equipment_inventory_row(disk_root):
    """INC-1001 mentions Asset MBP-2026-014; that asset must exist in
    IT_Equipment_Inventory assigned to Alex Rivera."""
    ticket_dir = disk_root / "tickets/queues/it-helpdesk/open"
    candidates = [p for p in ticket_dir.iterdir()
                  if p.name.startswith("INC-1001__")]
    assert candidates, "INC-1001 missing"
    body = _read_json(candidates[0])["body"]
    assert "MBP-2026-014" in body
    inv = _gsheet_cells(
        disk_root / "sheets/owned"
        / "2026-05-12_IT_Equipment_Inventory__SH102.gsheet.json")
    matching_rows = [r for r in inv if r and r[0] == "MBP-2026-014"]
    assert matching_rows, "MBP-2026-014 not in inventory"
    assert matching_rows[0][4] == "Alex Rivera"
    assert matching_rows[0][6] == "in-shipping"


def test_inc_1004_references_access_matrix_role(disk_root):
    """INC-1004 routes to acme-platform GitHub org; the Access Matrix
    must list that org for Software Engineer / Platform."""
    ticket_dir = disk_root / "tickets/queues/it-helpdesk/open"
    candidates = [p for p in ticket_dir.iterdir()
                  if p.name.startswith("INC-1004__")]
    assert candidates, "INC-1004 missing"
    body = _read_json(candidates[0])["body"]
    assert "acme-platform" in body
    matrix = _gsheet_cells(
        disk_root / "sheets/owned"
        / "2026-05-12_Access_Matrix__SH103.gsheet.json")
    platform_rows = [r for r in matrix
                     if len(r) >= 3 and r[0] == "Software Engineer"
                     and r[1] == "Platform"]
    assert platform_rows, "Software Engineer / Platform row missing"
    assert "acme-platform" in platform_rows[0][2]


def test_postmortem_aligns_with_new_hire_tracker(disk_root):
    """Slack outage postmortem GD105 says two hires (Priya Wong, Marcus
    Davis) had Day 1 on the outage date 2026-04-22; the New Hire Tracker
    must list those rows."""
    pm_doc = _read_json(
        disk_root / "gdocs/owned"
        / "2026-04-22_Slack_Outage_Postmortem__GD105.gdoc.json")
    pm_text = "".join(
        elt["textRun"]["content"]
        for c in pm_doc["body"]["content"]
        if "paragraph" in c
        for elt in c["paragraph"]["elements"]
        if "textRun" in elt
    )
    assert "Priya Wong" in pm_text and "Marcus Davis" in pm_text
    tracker = _gsheet_cells(
        disk_root / "sheets/owned"
        / "2026-05-12_New_Hire_Tracker__SH101.gsheet.json")
    names = {r[0] for r in tracker if r}
    assert "Priya Wong" in names
    assert "Marcus Davis" in names


def test_inc_1006_is_near_duplicate_of_inc_1002(disk_root):
    """INC-1006 (Slack workspace access) and INC-1002 (AWS access) are
    intentionally near-duplicates for the triage task. Both mention Alex
    Rivera and reference INC-1003 (the Okta SSO ticket)."""
    open_dir = disk_root / "tickets/queues/it-helpdesk/open"
    by_id: dict[str, dict] = {}
    for p in open_dir.iterdir():
        if "__" in p.name and p.name.endswith(".json"):
            tid = p.name.split("__", 1)[0]
            by_id[tid] = _read_json(p)
    assert "INC-1002" in by_id and "INC-1006" in by_id
    assert by_id["INC-1002"]["requester"]["name"] == "Alex Rivera"
    assert by_id["INC-1006"]["requester"]["name"] == "Alex Rivera"
    assert "INC-1003" in by_id["INC-1002"]["related_tickets"]
    assert "INC-1003" in by_id["INC-1006"]["related_tickets"]


def test_alex_dms_with_diana_and_sam_exist(disk_root):
    """The onboarding_status task requires Alex's DMs with Diana and Sam."""
    dms_root = disk_root / "slack/dms"
    diana_dirs = list(dms_root.glob("diana__*"))
    sam_dirs = list(dms_root.glob("sam__*"))
    assert diana_dirs, "Diana DM dir missing"
    assert sam_dirs, "Sam DM dir missing"
    assert any(p.glob("*/chat.jsonl") for p in diana_dirs)
    assert any(p.glob("*/chat.jsonl") for p in sam_dirs)


def test_bob_is_distinct_persona_from_alex(disk_root):
    """Bob Lee is the control persona; he must appear as a separate
    requester on his own tickets, never as Alex."""
    open_dir = disk_root / "tickets/queues/it-helpdesk/open"
    bob_tickets = [
        _read_json(p) for p in open_dir.iterdir()
        if p.name.startswith("INC-1005__")
    ]
    assert bob_tickets
    assert bob_tickets[0]["requester"]["name"] == "Bob Lee"
    assert "alex" not in bob_tickets[0]["body"].lower()
