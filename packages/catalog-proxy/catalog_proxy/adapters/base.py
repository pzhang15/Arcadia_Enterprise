from __future__ import annotations

import abc
from typing import Any


class BaseAdapter(abc.ABC):
    """Abstract base for data source adapters.

    Each adapter translates catalog operations into the native protocol
    of a specific data source (Iceberg REST, Snowflake SQL API, MCP,
    PostgreSQL wire protocol, S3 listing API, etc.).
    """

    source_type: str = "unknown"

    @abc.abstractmethod
    async def list_tables(self) -> list[str]:
        """Return all table/resource names available from this source."""

    @abc.abstractmethod
    async def get_schema(self, table: str) -> dict[str, Any]:
        """Return the schema for a table as a JSON-serialisable dict.

        Args:
            table (str): Table or resource name.
        """

    @abc.abstractmethod
    async def get_sample(self, table: str, limit: int = 10) -> list[dict[str, Any]]:
        """Return sample rows from a table.

        Args:
            table (str): Table or resource name.
            limit (int): Maximum number of rows.
        """

    @abc.abstractmethod
    async def execute(self, table: str, query: dict[str, Any]) -> Any:
        """Execute a query spec and return results.

        Args:
            table (str): Table or resource name.
            query (dict[str, Any]): Query specification from query.json.
        """
