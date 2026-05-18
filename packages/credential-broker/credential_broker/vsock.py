from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class VsockChannel:
    """Communication channel over Firecracker's virtio-vsock.

    Provides a host-to-guest communication path that does not traverse
    the network and is not accessible from outside the VM.  Used for
    secure credential injection into the sandbox.
    """

    def __init__(self, cid: int, port: int) -> None:
        self._cid = cid
        self._port = port

    async def listen(self) -> None:
        """Start listening for credential requests from the guest."""
        raise NotImplementedError

    async def send(self, payload: bytes) -> None:
        """Send a credential payload to the guest.

        Args:
            payload (bytes): Serialised token data.
        """
        raise NotImplementedError
