import argparse
import asyncio
import os
import sys

from agents import Runner
from agents.run import RunConfig
from agents.sandbox import SandboxAgent, SandboxRunConfig
from dotenv import load_dotenv

from mirage import MountMode, Workspace
from mirage.agents.openai_agents import MirageSandboxClient
from mirage.resource.gdrive import GoogleDriveConfig, GoogleDriveResource
from mirage.resource.gsheets import GSheetsConfig, GSheetsResource
from mirage.resource.ram import RAMResource
from mirage.resource.slack import SlackConfig, SlackResource

load_dotenv(".env.development")

PRESET_TASKS = {
    "weekly-status": (
        "Find my most recently modified spreadsheet under /sheets/owned/. "
        "Treat it as a project tracker. For each row marked 'in progress' "
        "or 'in_progress' (case-insensitive), search Slack for the most "
        "recent message I sent that mentions the project name -- check both "
        "channels and DMs. Write a one-page weekly status doc to /status.md "
        "with one section per project covering: what shipped, what's "
        "blocked, what's next. Be concise -- no filler."),
    "1on1-prep": (
        "I have a 1:1 with {person} tomorrow. Search Slack DMs with them "
        "from the last 14 days. Also list any GDocs under /gdrive/ that "
        "they appear in (by name) recently. Produce a 5-bullet "
        "talking-points doc to /1on1.md covering: open threads we owe each "
        "other, recent decisions, and 2 questions I should ask them."),
    "project-brief": (
        "Find every Slack thread, GDoc, and Sheet that mentions '{project}'. "
        "Synthesize a one-page brief to /brief.md with sections: Scope, "
        "Current Status, Owners, Open Questions, Links. Include direct "
        "links to the source artifacts."),
}


def build_workspace() -> Workspace:
    google_kwargs = dict(
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
    )
    slack = SlackResource(config=SlackConfig(
        token=os.environ["SLACK_BOT_TOKEN"],
        search_token=os.environ.get("SLACK_USER_TOKEN"),
    ))
    sheets = GSheetsResource(config=GSheetsConfig(**google_kwargs))
    gdrive = GoogleDriveResource(config=GoogleDriveConfig(**google_kwargs))
    return Workspace(
        {
            "/": (RAMResource(), MountMode.WRITE),
            "/slack": (slack, MountMode.WRITE),
            "/sheets": (sheets, MountMode.WRITE),
            "/gdrive": (gdrive, MountMode.WRITE),
        },
        mode=MountMode.WRITE,
        agent_id="customer-zero",
        session_id="phase0",
    )


async def run_task(task: str) -> None:
    ws = build_workspace()
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
        "find / \\( -path /slack -o -path /sheets -o -path /gdrive "
        "-o -path /.sessions \\) -prune -o -type f -print")
    print((listing.stdout or b"").decode())
    print("\n=== where to read the trace ===")
    print("  cat /.sessions/$(date +%Y-%m-%d)/phase0.jsonl | jq")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 0 personal-productivity agent over "
        "Slack + Sheets + GDrive.")
    parser.add_argument(
        "task",
        nargs="?",
        help=("Either a preset name (" + ", ".join(PRESET_TASKS) +
              ") or a free-text prompt."),
    )
    parser.add_argument("--person",
                        default="my manager",
                        help="Substituted into 1on1-prep preset.")
    parser.add_argument("--project",
                        default="MIRAGE",
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
    asyncio.run(run_task(task))


if __name__ == "__main__":
    main()
