import argparse

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from mirage_eval.scenario import ENTERPRISE_ROOT, ScenarioManifest

_ws = None
_mcp = FastMCP("mirage")


def _build_workspace(scenario: str, surface: str = "l1"):
    global _ws
    manifest = ScenarioManifest.load(scenario)
    builder = manifest.get_builder(surface)
    _ws = builder(agent_id="mcp-server", session_id="default")
    return _ws


@_mcp.tool()
async def execute(command: str) -> str:
    """Execute a shell command in the Mirage workspace.

    The workspace is a virtual filesystem with mounted enterprise data
    (Slack, tickets, GitHub, PagerDuty, Datadog, etc.). Use standard
    shell commands: ls, cat, head, grep, jq, find, tree.

    Args:
        command (str): Shell command to execute.
    """
    if _ws is None:
        return "ERROR: workspace not initialized"
    result = await _ws.execute(command)
    stdout = (result.stdout or b"").decode(errors="replace")
    stderr = (result.stderr or b"").decode(errors="replace")
    parts = []
    if stdout.strip():
        parts.append(stdout.rstrip())
    if stderr.strip():
        parts.append(f"[stderr] {stderr.rstrip()}")
    exit_code = getattr(result, "exit_code", None)
    if exit_code and exit_code != 0:
        parts.append(f"[exit_code={exit_code}]")
    return "\n".join(parts) or "(no output)"


@_mcp.prompt()
def workspace_guide() -> str:
    """Navigation guide for the mounted workspace.

    Lists every mount point, its file layout, available commands, and
    jq paths. Request this prompt before exploring the workspace.
    """
    if _ws is None:
        return "Workspace not initialized."
    return _ws.file_prompt


def serve(scenario: str, surface: str = "l1",
          transport: str = "stdio", host: str = "127.0.0.1") -> None:
    """Build a workspace and run the MCP server.

    Args:
        scenario (str): Scenario id (e.g. ``meridian_labs``).
        surface (str): ``l1`` (synthetic) or ``l2`` (real APIs).
        transport (str): ``stdio`` (default) or ``streamable-http``.
        host (str): Bind address for HTTP transports (default 127.0.0.1,
            use 0.0.0.0 for Docker).
    """
    load_dotenv(ENTERPRISE_ROOT / ".env")
    load_dotenv(ENTERPRISE_ROOT.parent / ".env.development")
    _build_workspace(scenario, surface)
    if transport != "stdio":
        _mcp.settings.host = host
    _mcp.run(transport=transport)


def main() -> None:
    """Standalone entry point for ``mirage-mcp`` console script."""
    parser = argparse.ArgumentParser(
        description="Mirage MCP server")
    parser.add_argument("--scenario", required=True,
                        help="Scenario id (e.g. meridian_labs)")
    parser.add_argument("--surface", default="l1",
                        help="l1 (synthetic) or l2 (real APIs)")
    parser.add_argument("--transport", default="stdio",
                        choices=["stdio", "streamable-http"],
                        help="MCP transport (default: stdio)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Bind address for HTTP (default: 127.0.0.1, "
                        "use 0.0.0.0 for Docker)")
    args = parser.parse_args()
    serve(scenario=args.scenario, surface=args.surface,
          transport=args.transport, host=args.host)


if __name__ == "__main__":
    main()
