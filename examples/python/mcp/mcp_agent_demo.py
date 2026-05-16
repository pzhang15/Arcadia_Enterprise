import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(".env.development")

from agents import Agent, Runner
from agents.mcp import MCPServerStdio

ENTERPRISE_DIR = str(
    (Path(__file__).resolve().parent.parent.parent.parent / "enterprise"))

TASK_PROMPT = (
    "Investigate the active critical incident on payments-api. "
    "Start by checking /pagerduty/incidents/triggered/ for active alerts, "
    "then find the linked Jira ticket in /tickets/queues/ops/open/, "
    "read the Slack #incidents channel at /slack/channels/incidents__C001/, "
    "check recent deployments at /github/repos/meridian-labs/payments-api/"
    "deployments/, read the commit that correlates, and check Datadog logs "
    "at /datadog/logs/payments-api/ and metrics at /datadog/metrics/"
    "payments-api/. Write a root-cause analysis to /incident_report.md."
)


async def main():
    async with MCPServerStdio(
        name="mirage-meridian-labs",
        params={
            "command": "uv",
            "args": [
                "run", "--directory", ENTERPRISE_DIR,
                "mirage-mcp", "--scenario", "meridian_labs",
            ],
        },
    ) as server:
        tools = await server.list_tools()
        print(f"MCP tools available: {[t.name for t in tools]}")

        agent = Agent(
            name="SRE Investigator",
            instructions=(
                "You are a senior SRE at Meridian Labs. Use the execute "
                "tool to run shell commands (ls, cat, grep, jq) against "
                "the workspace to investigate incidents. Be thorough: "
                "cross-reference data across PagerDuty, tickets, Slack, "
                "GitHub, and Datadog before drawing conclusions."
            ),
            mcp_servers=[server],
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        )
        result = await Runner.run(agent, TASK_PROMPT)
        print("\n" + "=" * 60)
        print("AGENT OUTPUT")
        print("=" * 60)
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
