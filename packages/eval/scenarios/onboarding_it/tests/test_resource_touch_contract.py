"""Run the oracle pipeline and assert the mounts touched match what
the task YAML's `ops_must_touch_prefix` / `ops_must_not_touch_prefix`
declare. This pins the resource contract."""
import pytest
from mirage_eval.scenario import ScenarioManifest


@pytest.mark.asyncio
async def test_onboarding_status_oracle_touches_required_mounts(l1_workspace):
    ws = l1_workspace
    pre = len(ws.ops.records)
    cmds = [
        "cat /sheets/owned/2026-05-12_New_Hire_Tracker__SH101.gsheet.json "
        "> /dev/null",
        "ls /tickets/queues/it-helpdesk/open/",
        "for f in /tickets/queues/it-helpdesk/open/INC-100[124]*.json; "
        "do cat $f > /dev/null; done",
        "cat /slack/channels/onboarding__C302/2026-05-12/chat.jsonl "
        "> /dev/null",
        "cat /slack/dms/diana__D201/2026-05-11/chat.jsonl > /dev/null",
        "cat /slack/dms/sam__D202/2026-05-12/chat.jsonl > /dev/null",
    ]
    for cmd in cmds:
        r = await ws.execute(cmd)
        assert r.exit_code == 0, (cmd, (r.stderr or b"").decode())
    records = ws.ops.records[pre:]
    paths = sorted({r.path for r in records if r.path})
    manifest = ScenarioManifest.load("onboarding_it")
    task = manifest.load_task("onboarding_status")
    from mirage_eval.scorers.programmatic import _matches_prefix
    for required in task.oracles.ops_must_touch_prefix:
        assert _matches_prefix(
            paths, required), (f"required prefix {required!r} not touched; "
                               f"touched: {paths[:20]}...")
    for forbidden in task.oracles.ops_must_not_touch_prefix:
        assert not _matches_prefix(
            paths, forbidden), (f"forbidden prefix {forbidden!r} touched")
