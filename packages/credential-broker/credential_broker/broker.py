from __future__ import annotations

import logging
from typing import Any

from credential_broker.store import CredentialStore

logger = logging.getLogger(__name__)


class CredentialBroker:
    """Host-side credential broker.

    Manages authentication tokens for external data sources. Runs
    outside the sandbox boundary and communicates with the in-guest
    Catalog Proxy via virtio-vsock, issuing only short-lived,
    tightly-scoped tokens.
    """

    def __init__(self, store: CredentialStore) -> None:
        self._store = store

    async def issue_token(self,
                          source_id: str,
                          scopes: list[str],
                          ttl_seconds: int = 300) -> dict[str, Any]:
        """Issue a short-lived, scoped token for a data source.

        Args:
            source_id (str): Data source identifier.
            scopes (list[str]): Authorized resource scopes.
            ttl_seconds (int): Token time-to-live.
        """
        raise NotImplementedError

    async def refresh_token(self, token_id: str) -> dict[str, Any]:
        """Refresh an expiring token.

        Args:
            token_id (str): Existing token identifier.
        """
        raise NotImplementedError

    async def revoke_token(self, token_id: str) -> None:
        """Revoke a token immediately.

        Args:
            token_id (str): Token to revoke.
        """
        raise NotImplementedError
