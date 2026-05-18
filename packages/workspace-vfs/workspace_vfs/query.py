from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class QuerySpec(BaseModel):
    """A query.json specification written by the agent.

    The agent writes this file; the VFS materialises results into
    result.parquet.  The ``type`` field selects the query semantics.
    """

    type: str
    source: str | None = None
    table: str | None = None
    columns: list[str] | None = None
    where: dict[str, Any] | None = None
    limit: int | None = None
    pattern: str | None = None
    vector: list[float] | None = None
    top_k: int | None = None
    query_text: str | None = None

    def validate_for_type(self) -> None:
        """Raise ValueError if required fields for the query type are missing."""
        validators: dict[str, list[str]] = {
            "sql": ["source", "table"],
            "glob": ["pattern"],
            "similarity": ["vector", "top_k"],
            "search": ["query_text"],
        }
        required = validators.get(self.type, [])
        missing = [f for f in required if getattr(self, f) is None]
        if missing:
            raise ValueError(
                f"query type {self.type!r} requires fields: {missing}")
