from __future__ import annotations

import hashlib
import os
import random
import struct
from typing import Callable, Sequence, TypeVar

T = TypeVar("T")

DST_SEED_ENV = "DST_SEED"

_DERIVE_DOMAIN = b"mirage_dstest.rng.derive\x00"
_FORK_DOMAIN = b"mirage_dstest.rng.fork\x00"
_MASK_64 = (1 << 64) - 1
_UNIT_DENOM = float(1 << 64)


def _encode_str(value: str) -> bytes:
    """Length-prefix a UTF-8 string so distinct field tuples never collide.

    Encodes ``len(raw)`` as an unsigned 64-bit little-endian prefix followed
    by the raw bytes, making ``("a", "bc")`` and ``("ab", "c")`` hash to
    different digests.

    Args:
        value (str): Text field to encode.
    """
    raw = value.encode("utf-8")
    return struct.pack("<Q", len(raw)) + raw


def _derive_digest(domain: bytes, seed: int, op_index: int, site: str,
                   key: str) -> bytes:
    """Return the blake2b digest for a canonical (seed, op_index, site, key).

    The encoding is unambiguous: a fixed domain tag, the seed and op_index as
    signed 64-bit little-endian integers, then length-prefixed site and key.
    The same inputs always yield the same digest regardless of call order,
    which is the replay-by-seed invariant.

    Args:
        domain (bytes): Domain-separation tag distinguishing draw kinds.
        seed (int): Master seed of the stream.
        op_index (int): Monotonic operation index of the decision site.
        site (str): Logical decision-site label.
        key (str): Per-site key (e.g. a path) the decision is scoped to.
    """
    canonical = (
        domain
        + struct.pack("<q", seed)
        + struct.pack("<q", op_index)
        + _encode_str(site)
        + _encode_str(key)
    )
    return hashlib.blake2b(canonical, digest_size=8).digest()


class SeededRandom:
    """Seeded RNG façade with replay-invariant per-decision derived draws.

    Wraps ``random.Random`` for general sequential draws (``random``,
    ``randint``, ``choice``, ``getrandbits``) used for things like minting
    fork IDs. For fault decisions it exposes ``derive_unit`` / ``derive_int``,
    which hash ``(seed, op_index, site, key)`` with blake2b so the draw for a
    given operation site is a pure function of its coordinates. Those derived
    draws never consume the master stream, so they are invariant to async
    interleaving: op #N at site S on key K always yields the same value no
    matter the order decisions are evaluated.

    Args:
        seed (int): Master seed for the stream and the derivation root.
    """

    def __init__(self, seed: int) -> None:
        self._seed = seed
        self._random = random.Random(seed)

    @property
    def seed(self) -> int:
        """Return the master seed this stream was constructed with."""
        return self._seed

    def random(self) -> float:
        """Return the next ``[0, 1)`` float from the master stream."""
        return self._random.random()

    def randint(self, a: int, b: int) -> int:
        """Return a master-stream integer ``N`` such that ``a <= N <= b``.

        Args:
            a (int): Inclusive lower bound.
            b (int): Inclusive upper bound.
        """
        return self._random.randint(a, b)

    def choice(self, seq: Sequence[T]) -> T:
        """Return a master-stream random element of a non-empty sequence.

        Args:
            seq (Sequence[T]): Non-empty sequence to choose from.
        """
        return self._random.choice(seq)

    def getrandbits(self, k: int) -> int:
        """Return a master-stream integer with ``k`` random bits.

        Args:
            k (int): Number of random bits to draw (``k >= 0``).
        """
        return self._random.getrandbits(k)

    def derive_unit(self, *, op_index: int, site: str, key: str) -> float:
        """Return a replay-invariant ``[0, 1)`` draw for an operation site.

        Computes ``blake2b(seed, op_index, site, key)`` and maps its first 8
        bytes to a unit float. Independent of the master stream and of call
        order, so it is the backbone for deterministic fault decisions under
        arbitrary async interleaving.

        Args:
            op_index (int): Monotonic operation index of the decision site.
            site (str): Logical decision-site label.
            key (str): Per-site key (e.g. a path) the decision is scoped to.
        """
        digest = _derive_digest(_DERIVE_DOMAIN, self._seed, op_index, site,
                                key)
        return (struct.unpack("<Q", digest)[0] & _MASK_64) / _UNIT_DENOM

    def derive_int(self, *, op_index: int, site: str, key: str,
                   bound: int) -> int:
        """Return a replay-invariant integer in ``[0, bound)`` for a site.

        Derives a unit float via the same hashing as ``derive_unit`` and
        scales it into ``[0, bound)``. Pure in its inputs and independent of
        the master stream.

        Args:
            op_index (int): Monotonic operation index of the decision site.
            site (str): Logical decision-site label.
            key (str): Per-site key (e.g. a path) the decision is scoped to.
            bound (int): Exclusive upper bound (must be ``>= 1``).
        """
        if bound < 1:
            raise ValueError(f"bound must be >= 1, got {bound}")
        digest = _derive_digest(_DERIVE_DOMAIN, self._seed, op_index, site,
                                key)
        value = struct.unpack("<Q", digest)[0] & _MASK_64
        return value % bound

    def fork_child(self, label: str) -> "SeededRandom":
        """Return a deterministic child stream seeded from a label.

        The child seed is derived by hashing the parent seed with the label,
        so the same parent seed and label always produce the same child
        stream while different labels yield independent streams.

        Args:
            label (str): Stable label identifying the child sub-stream.
        """
        digest = _derive_digest(_FORK_DOMAIN, self._seed, 0, "fork", label)
        child_seed = struct.unpack("<q", digest)[0]
        return SeededRandom(child_seed)


def _missing_default() -> int:
    """Raise because no ``DST_SEED`` is set and no default factory was given.

    Determinism rule: this function never consults wall-clock time or
    ``SystemRandom``. Callers that want a fresh seed must pass their own
    (seeded) factory explicitly.
    """
    raise RuntimeError(
        f"{DST_SEED_ENV} is not set and no default_factory was provided; "
        "refusing to invent a seed (determinism rule)."
    )


def seed_from_env(default_factory: Callable[[], int] = _missing_default) -> int:
    """Return the run seed from the ``DST_SEED`` environment variable.

    Reads ``DST_SEED`` and parses it as an integer when present. When the
    variable is unset or empty, calls ``default_factory`` to obtain the seed.
    This function itself never reads the clock or unseeded randomness; any
    time- or entropy-based behavior must come from a factory the caller
    explicitly supplies.

    Args:
        default_factory (Callable[[], int]): Zero-argument callable returning
            a fallback seed when ``DST_SEED`` is absent. Defaults to a factory
            that raises, so a seed is never silently invented.
    """
    raw = os.environ.get(DST_SEED_ENV)
    if raw is None or raw.strip() == "":
        return default_factory()
    try:
        return int(raw.strip(), 0)
    except ValueError as exc:
        raise ValueError(
            f"{DST_SEED_ENV}={raw!r} is not a valid integer seed"
        ) from exc
