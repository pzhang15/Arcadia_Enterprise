from __future__ import annotations

from typing import Any

from catalog_proxy.adapters.base import BaseAdapter


class McpAdapter(BaseAdapter):
    """Adapter for SaaS tools accessed via Model Context Protocol servers.

    Wraps MCP resources (Jira, Slack, Google Drive, Salesforce, etc.)
    and maps them into the VFS directory tree.  Replaces the need for
    individual MCP tool definitions in the agent's context window.
    """

    source_type: str = "mcp"

    def __init__(self, server_url: str) -> None:
        self._server_url = server_url

    async def list_tables(self) -> list[str]:
        raise NotImplementedError

    async def get_schema(self, table: str) -> dict[str, Any]:
        raise NotImplementedError

    async def get_sample(self,
                         table: str,
                         limit: int = 10) -> list[dict[str, Any]]:
        raise NotImplementedError

    async def execute(self, table: str, query: dict[str, Any]) -> Any:
        raise NotImplementedError
