from __future__ import annotations

import abc
from typing import Any


class BaseSink(abc.ABC):
    """Abstract lineage event sink.

    Implementations send events to OpenLineage-compatible backends
    (Marquez, Unity Catalog lineage, custom HTTP endpoints, local files).
    """

    @abc.abstractmethod
    async def emit(self, event: dict[str, Any]) -> None:
        """Publish a single lineage event.

        Args:
            event (dict[str, Any]): OpenLineage-formatted event.
        """
