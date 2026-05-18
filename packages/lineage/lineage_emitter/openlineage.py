from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class OpenLineageEvent(BaseModel):
    """OpenLineage-compatible event schema.

    Conforms to the OpenLineage spec for recording data access,
    transformation, and derivation relationships.
    """

    event_type: str
    event_time: str
    producer: str = "arcadia-lineage"
    schema_url: str = "https://openlineage.io/spec/2-0-2/OpenLineage.json"
    run: dict[str, Any]
    job: dict[str, Any]
    inputs: list[dict[str, Any]] = []
    outputs: list[dict[str, Any]] = []
