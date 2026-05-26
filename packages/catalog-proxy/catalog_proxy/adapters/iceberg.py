from __future__ import annotations

from typing import Any

from catalog_proxy.adapters.base import BaseAdapter


class IcebergAdapter(BaseAdapter):
    """Adapter for Apache Iceberg tables via the Iceberg REST Catalog API.

    Speaks the ~20-endpoint Iceberg REST spec and translates catalog
    metadata into the VFS tree structure.
    """

    source_type: str = "iceberg"

    def __init__(self, catalog_url: str, warehouse: str) -> None:
        self._catalog_url = catalog_url
        self._warehouse = warehouse

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
