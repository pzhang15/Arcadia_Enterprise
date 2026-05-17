import argparse
import asyncio
import os
import sys
from pathlib import Path

from agents import Runner
from agents.run import RunConfig
from agents.sandbox import SandboxAgent, SandboxRunConfig
from dotenv import load_dotenv

from examples.python.demo.local_enterprise.fake_resources import (
    FakeGDocsResource, FakeGSheetsResource, FakeSlackResource)
from mirage import MountMode, Workspace
from mirage.agents.openai_agents import MirageSandboxClient
from mirage.resource.ram import RAMResource

load_dotenv(".env.development")

PRESET_TASKS = {
    "weekly-status": (
        "Read the Q2 Project Tracker spreadsheet under /sheets/owned/. "
        "For each row whose Status is 'in_progress' (case-insensitive), find "
        "the most recent Slack message in the linked Slack Channel that "
        "discusses progress, blockers, or wins for that project. Combine "
        "with the row's Notes column. Write a one-page weekly status doc to "
        "/status.md with one section per project covering: what shipped, "
        "what's blocked, what's next. Be concise -- no filler. End with a "
        "'Risks' section listing anything OKR-at-risk from /sheets/owned/ "
        "(Q2 OKRs spreadsheet)."),
    "1on1-prep": (
        "I have a 1:1 with {person} tomorrow. (1) Identify their Slack DM "
        "channel under /slack/dms/. (2) Summarize our DM conversation from "
        "the last 7 days. (3) List any GDocs under /gdocs/owned/ that "
        "mention their name or that we've both touched. (4) Cross-reference "
        "Slack channels they post in. Produce a 5-bullet talking-points doc "
        "to /1on1.md covering: open threads we owe each other, recent "
        "decisions, and 2 questions I should ask them. Be specific -- cite "
        "messages or doc sections, don't summarize generically."),
    "project-brief": (
        "Find every Slack thread, GDoc, and Sheet that mentions '{project}'. "
        "Synthesize a one-page brief to /brief.md with sections: Scope, "
        "Current Status, Owners, Open Questions, Links. Include direct "
        "references to source artifacts (channel/date or doc title)."),
    "cross-system": (
        "There is a P1 customer escalation about Acme losing data on a "
        "migration. (1) Find the relevant thread in /slack/channels/. "
        "(2) Find the linked engineering discussion. (3) Find the postmortem "
        "doc under /gdocs/owned/. (4) Find any related row in the Q2 "
        "Project Tracker. Write an exec-readable incident summary to "
        "/incident.md with: timeline, root cause, mitigation, action items, "
        "customer status."),
}


def build_workspace(root: Path) -> Workspace:
    slack_root = root / "slack"
    sheets_root = root / "sheets"
    gdocs_root = root / "gdocs"
    for p in (slack_root, sheets_root, gdocs_root):
        if not p.exists():
            sys.exit(f"missing {p} -- run seed.py first")
    return Workspace(
        {
            "/": (RAMResource(), MountMode.WRITE),
            "/slack": (FakeSlackResource(root=str(slack_root)), MountMode.READ),
            "/sheets": (FakeGSheetsResource(root=str(sheets_root)), MountMode.READ),
            "/gdocs": (FakeGDocsResource(root=str(gdocs_root)), MountMode.READ),
        },
        mode=MountMode.WRITE,
        agent_id="customer-zero",
        session_id="phase0",
    )


async def run_task(task: str, root: Path) -> None:
    ws = build_workspace(root)
    client = MirageSandboxClient(ws)
    agent = SandboxAgent(
        name="Personal Productivity Agent",
        model=os.environ.get("OPENAI_MODEL", "gpt-5-mini"),
        instructions=ws.file_prompt,
    )
    print(f"\n=== task ===\n{task}\n")
    result = await Runner.run(
        agent,
        task,
        run_config=RunConfig(sandbox=SandboxRunConfig(client=client)),
    )
    print("\n=== final output ===")
    print(result.final_output)
    print("\n=== files in / (RAM) ===")
    listing = await ws.execute(
        "find / \\( -path /slack -o -path /sheets -o -path /gdocs "
        "-o -path /.sessions \\) -prune -o -type f -print")
    print((listing.stdout or b"").decode())
    for fname in ("/status.md", "/1on1.md", "/brief.md", "/incident.md"):
        check = await ws.execute(f"test -f {fname} && cat {fname}")
        body = (check.stdout or b"").decode()
        if body.strip():
            print(f"\n=== {fname} ===")
            print(body)
    print("\n=== trace location (inside the workspace) ===")
    trace = await ws.execute("ls /.sessions/")
    print((trace.stdout or b"").decode())
    print("Use: cat /.sessions/<date>/phase0.jsonl")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 0 personal-productivity agent over a synthetic "
        "local enterprise workspace.")
    parser.add_argument(
        "task",
        nargs="?",
        help=("Either a preset name (" + ", ".join(PRESET_TASKS) +
              ") or a free-text prompt."),
    )
    parser.add_argument("--root", default="~/mirage-demo",
                        help="Synthetic workspace root (default ~/mirage-demo).")
    parser.add_argument("--person", default="sridhar",
                        help="Substituted into 1on1-prep preset.")
    parser.add_argument("--project", default="Aurora",
                        help="Substituted into project-brief preset.")
    args = parser.parse_args()
    if args.task is None:
        print("usage: personal_agent.py <preset|free-text>")
        print("presets:", ", ".join(PRESET_TASKS))
        sys.exit(2)
    if args.task in PRESET_TASKS:
        task = PRESET_TASKS[args.task].format(person=args.person,
                                              project=args.project)
    else:
        task = args.task
    root = Path(args.root).expanduser().resolve()
    asyncio.run(run_task(task, root))


if __name__ == "__main__":
    main()
