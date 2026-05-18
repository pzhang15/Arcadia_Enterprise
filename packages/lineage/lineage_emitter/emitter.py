from __future__ import annotations

import logging
from typing import Any

from lineage_emitter.sinks.base import BaseSink

logger = logging.getLogger(__name__)


class LineageEmitter:
    """Captures VFS data access operations and publishes lineage events.

    Because the FUSE mount mediates all data access, every file read
    becomes a lineage event.  The emitter formats these into
    OpenLineage-compatible events and publishes to configured sinks.
    """

    def __init__(self, sinks: list[BaseSink] | None = None) -> None:
        self._sinks: list[BaseSink] = sinks or []

    def add_sink(self, sink: BaseSink) -> None:
        """Register an output sink.

        Args:
            sink (BaseSink): Sink instance.
        """
        self._sinks.append(sink)

    async def emit_read(
        self,
        session_id: str,
        source: str,
        table: str,
        columns: list[str],
        row_count: int,
        predicates: dict[str, Any] | None = None,
    ) -> None:
        """Emit a lineage event for a data read operation.

        Args:
            session_id (str): Agent session identifier.
            source (str): Data source name.
            table (str): Table or resource name.
            columns (list[str]): Columns accessed.
            row_count (int): Number of rows scanned.
            predicates (dict[str, Any] | None): Filter predicates applied.
        """
        raise NotImplementedError

    async def emit_write(
        self,
        session_id: str,
        output_path: str,
        inputs: list[dict[str, Any]],
    ) -> None:
        """Emit a lineage event for an agent output write.

        Args:
            session_id (str): Agent session identifier.
            output_path (str): Path under /workspace/_output/.
            inputs (list[dict[str, Any]]): Input lineage references.
        """
        raise NotImplementedError
