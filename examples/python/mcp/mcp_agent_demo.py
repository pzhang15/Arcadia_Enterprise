import argparse
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

ENTERPRISE_DIR = str(
    (Path(__file__).resolve().parent.parent.parent.parent / "enterprise"))

load_dotenv(Path(ENTERPRISE_DIR) / ".env")
load_dotenv(".env.development")

from openai import AsyncOpenAI

from agents import Agent, Runner
from agents.mcp import MCPServerStdio, MCPServerStreamableHttp
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

INSTRUCTIONS = (
    "You are a senior SRE at Meridian Labs, a fintech company running a "
    "payments API platform. Use the execute tool to run shell commands "
    "(ls, cat, grep, jq) against the workspace.\n\n"
    "The workspace is a virtual filesystem with mounted enterprise data:\n"
    "  /pagerduty/  — incidents and services\n"
    "  /tickets/    — Jira-style ticket queues (OPS, PAY)\n"
    "  /slack/      — channel messages and user profiles\n"
    "  /github/     — deployments, commits, pull requests\n"
    "  /datadog/    — logs and metrics\n\n"
    "Always start with `ls` to discover the structure before reading "
    "files. Cross-reference data across all services before concluding."
)

TASK_PROMPT = (
    "Investigate the active critical incident on payments-api.\n\n"
    "1. Check /pagerduty/incidents/triggered/ for active alerts\n"
    "2. Find the linked Jira ticket in /tickets/queues/ops/open/\n"
    "3. Read the Slack #incidents channel at "
    "/slack/channels/incidents__C001/\n"
    "4. Check recent deployments at "
    "/github/repos/meridian-labs/payments-api/deployments/\n"
    "5. Read the commit that correlates with the incident\n"
    "6. Check Datadog logs at /datadog/logs/payments-api/ and metrics "
    "at /datadog/metrics/payments-api/\n\n"
    "Write a root-cause analysis to /incident_report.md with sections: "
    "Incident Summary, Root Cause, Evidence, Recommended Action."
)


def _build_local_server():
    return MCPServerStdio(
        name="mirage-meridian-labs",
        params={
            "command": "uv",
            "args": [
                "run", "--directory", ENTERPRISE_DIR,
                "python", "-m", "mirage_eval.mcp_server",
                "--scenario", "meridian_labs",
            ],
        },
    )


def _build_docker_server(url: str):
    return MCPServerStreamableHttp(
        name="mirage-meridian-labs-docker",
        params={"url": url},
    )


async def run_agent(mode: str, docker_url: str):
    server_ctx = (_build_docker_server(docker_url) if mode == "docker"
                  else _build_local_server())

    async with server_ctx as server:
        tools = await server.list_tools()
        print(f"Connected. Tools: {[t.name for t in tools]}")

        model_name = os.environ.get("OPENAI_MODEL", "gpt-4o")
        base_url = os.environ.get("OPENAI_BASE_URL", "")
        if base_url:
            client = AsyncOpenAI(base_url=base_url)
            model = OpenAIChatCompletionsModel(
                model=model_name, openai_client=client)
            os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
        else:
            model = model_name

        agent = Agent(
            name="SRE Investigator",
            instructions=INSTRUCTIONS,
            mcp_servers=[server],
            model=model,
        )
        result = await Runner.run(agent, TASK_PROMPT)
        print("\n" + "=" * 60)
        print("AGENT OUTPUT")
        print("=" * 60)
        print(result.final_output)


def main():
    parser = argparse.ArgumentParser(
        description="Run an SRE agent against Mirage via MCP")
    parser.add_argument(
        "--mode", choices=["local", "docker"], default="local",
        help="local: spawn mirage-mcp subprocess (stdio). "
             "docker: connect to running Docker MCP server (HTTP).")
    parser.add_argument(
        "--docker-url", default="http://localhost:8081/mcp",
        help="MCP server URL when using --mode docker")
    args = parser.parse_args()
    asyncio.run(run_agent(args.mode, args.docker_url))


if __name__ == "__main__":
    main()
