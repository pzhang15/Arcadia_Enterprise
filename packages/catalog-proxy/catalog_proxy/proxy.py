from __future__ import annotations

import logging
from typing import Any

from catalog_proxy.registry import SourceRegistry

logger = logging.getLogger(__name__)


class CatalogProxy:
    """Translation layer between the VFS and external data systems.

    Receives filesystem-level requests (readdir, read, getattr) from the
    FUSE mount, resolves them via the source registry, and returns
    formatted metadata or data through the appropriate adapter.
    """

    def __init__(self, registry: SourceRegistry) -> None:
        self._registry = registry

    async def resolve(self, path: str) -> dict[str, Any]:
        """Resolve a VFS path to catalog metadata.

        Args:
            path (str): Virtual filesystem path (e.g. "/analytics/customers/.schema").
        """
        raise NotImplementedError

    async def execute_query(self, source: str, table: str, query: dict[str, Any]) -> Any:
        """Execute a query.json spec against a source table.

        Args:
            source (str): Source identifier.
            table (str): Table name.
            query (dict[str, Any]): Query specification.
        """
        raise NotImplementedError
