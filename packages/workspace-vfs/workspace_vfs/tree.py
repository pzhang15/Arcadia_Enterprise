from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class WorkspaceTree:
    """Builds the /workspace/ directory tree from registered sources.

    Presents all authorized data sources as a navigable hierarchy that
    the agent explores with standard filesystem operations (ls, cat).
    Progressive disclosure: each level exposes only what is needed for
    the next decision.
    """

    def __init__(self) -> None:
        self._sources: dict[str, dict[str, Any]] = {}

    def register_source(self, mount_path: str, source_meta: dict[str,
                                                                 Any]) -> None:
        """Register a data source at a mount path.

        Args:
            mount_path (str): VFS path (e.g. "analytics", "jira", "slack").
            source_meta (dict[str, Any]): Source metadata for .manifest.
        """
        self._sources[mount_path] = source_meta

    def readdir(self, path: str) -> list[str]:
        """List entries at a VFS path.

        Args:
            path (str): Directory path relative to /workspace/.
        """
        raise NotImplementedError

    def getattr(self, path: str) -> dict[str, Any]:
        """Return file attributes for a VFS path.

        Args:
            path (str): File or directory path.
        """
        raise NotImplementedError
