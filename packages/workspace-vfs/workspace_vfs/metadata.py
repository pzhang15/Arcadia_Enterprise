from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SchemaFile(BaseModel):
    """Contents of a .schema dot-file for a table.

    Column definitions, types, descriptions, and access status
    (including DENIED with reason for governed columns).
    """

    columns: list[ColumnDef]
    primary_key: list[str] = []


class ColumnDef(BaseModel):
    """A single column definition within a .schema file."""

    name: str
    type: str
    description: str = ""
    access: str = "allowed"
    deny_reason: str | None = None


class PolicyFile(BaseModel):
    """Contents of a .policy dot-file for a table.

    Access rules: blocked columns, row filters, read-only flags,
    scan limits.
    """

    blocked_columns: list[str] = []
    row_filter: str | None = None
    read_only: bool = True
    max_scan_rows: int | None = None


class RelationshipEntry(BaseModel):
    """A cross-source relationship in a .relationships file.

    Join hints, foreign key mappings, regex patterns for extracting
    identifiers, and semantic equivalences.
    """

    source_a: str
    column_a: str
    source_b: str
    column_b: str
    relationship_type: str = "foreign_key"
    confidence: float = 1.0
    notes: str = ""


class StatsFile(BaseModel):
    """Contents of a .stats dot-file for a table."""

    row_count_estimate: int
    partition_columns: list[str] = []
    last_updated: str | None = None


class ManifestFile(BaseModel):
    """Contents of the top-level .manifest file.

    Provides discovery of all available sources, agent constraints,
    and budget information.
    """

    sources: list[dict[str, Any]]
    agent_id: str | None = None
    budget: dict[str, Any] | None = None
