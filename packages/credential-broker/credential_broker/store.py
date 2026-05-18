from __future__ import annotations

import abc
from typing import Any


class CredentialStore(abc.ABC):
    """Abstract credential storage backend.

    Implementations may use environment variables, a secrets manager
    (AWS Secrets Manager, HashiCorp Vault), or a local encrypted file.
    """

    @abc.abstractmethod
    async def get(self, source_id: str) -> dict[str, Any]:
        """Retrieve long-lived credentials for a source.

        Args:
            source_id (str): Data source identifier.
        """

    @abc.abstractmethod
    async def store(self, source_id: str, credentials: dict[str, Any]) -> None:
        """Persist credentials for a source.

        Args:
            source_id (str): Data source identifier.
            credentials (dict[str, Any]): Credential payload.
        """
