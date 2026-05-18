from __future__ import annotations

from typing import Any

from catalog_proxy.adapters.base import BaseAdapter


class SourceRegistry:
    """Registry of data source adapters.

    Maps source identifiers to their adapter instances.  The proxy
    consults this registry when resolving VFS paths to determine which
    adapter should handle the request.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, source_id: str, adapter: BaseAdapter) -> None:
        """Register an adapter for a source.

        Args:
            source_id (str): Unique identifier for this source.
            adapter (BaseAdapter): Adapter instance.
        """
        self._adapters[source_id] = adapter

    def get(self, source_id: str) -> BaseAdapter:
        """Return the adapter for a source.

        Args:
            source_id (str): Source identifier.

        Raises:
            KeyError: If no adapter is registered for the source.
        """
        return self._adapters[source_id]

    def list_sources(self) -> list[dict[str, Any]]:
        """Return metadata for all registered sources."""
        return [
            {"id": sid, "type": adapter.source_type}
            for sid, adapter in self._adapters.items()
        ]
