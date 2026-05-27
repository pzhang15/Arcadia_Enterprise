from __future__ import annotations

import logging
import threading
from collections import deque

from lineage_emitter.tracing.config import TraceConfig
from lineage_emitter.tracing.span import Span, TraceLevel

logger = logging.getLogger(__name__)

_DEFAULT_CAPACITY = {
    TraceLevel.AUDIT: 10_000,
    TraceLevel.TRACE: 50_000,
    TraceLevel.OPERATIONAL: 100_000,
}


class RingBuffer:
    """Thread-safe, priority-tiered ring buffer for completed spans.

    Each TraceLevel has its own fixed-capacity deque. When a tier is full,
    the oldest span in that tier is evicted — except AUDIT, which never
    evicts and instead signals back-pressure.

    Args:
        config (TraceConfig | None): Buffer capacity configuration.
    """

    def __init__(self, config: TraceConfig | None = None) -> None:
        cfg = config or TraceConfig()
        capacities = {
            TraceLevel.AUDIT: cfg.buffer_capacity_audit,
            TraceLevel.TRACE: cfg.buffer_capacity_trace,
            TraceLevel.OPERATIONAL: cfg.buffer_capacity_operational,
        }
        self._tiers: dict[TraceLevel, deque[Span]] = {
            level: deque(maxlen=cap)
            for level, cap in capacities.items()
        }
        self._lock = threading.Lock()
        self._dropped: dict[TraceLevel, int] = {
            level: 0
            for level in TraceLevel
        }

    def append(self, span: Span) -> bool:
        """Append a completed span to the appropriate tier.

        Returns False only when AUDIT tier is at capacity (back-pressure
        signal). TRACE and OPERATIONAL tiers silently evict the oldest
        span when full.

        Args:
            span (Span): Completed span to buffer.

        Returns:
            bool: True if accepted, False if AUDIT back-pressure.
        """
        tier = self._tiers.get(span.level)
        if tier is None:
            logger.warning("Unknown TraceLevel %s, dropping span %s",
                           span.level, span.span_id)
            return False

        with self._lock:
            if span.level == TraceLevel.AUDIT and len(tier) >= tier.maxlen:
                logger.error("AUDIT ring buffer full — back-pressure active")
                return False

            at_capacity = tier.maxlen is not None and len(tier) >= tier.maxlen
            if at_capacity:
                self._dropped[span.level] += 1
            tier.append(span)
            return True

    def drain(self, level: TraceLevel | None = None) -> list[Span]:
        """Remove and return all spans from the specified tier, or all tiers.

        Args:
            level (TraceLevel | None): Specific tier to drain, or None for all.

        Returns:
            list[Span]: Drained spans ordered by start_time_ms.
        """
        result: list[Span] = []
        with self._lock:
            if level is not None:
                tier = self._tiers.get(level)
                if tier:
                    result.extend(tier)
                    tier.clear()
            else:
                for tier in self._tiers.values():
                    result.extend(tier)
                    tier.clear()
        result.sort(key=lambda s: s.start_time_ms)
        return result

    def stats(self) -> dict[str, int]:
        """Return current buffer sizes and drop counts per tier."""
        with self._lock:
            return {
                "audit_buffered": len(self._tiers[TraceLevel.AUDIT]),
                "trace_buffered": len(self._tiers[TraceLevel.TRACE]),
                "operational_buffered":
                len(self._tiers[TraceLevel.OPERATIONAL]),
                "audit_dropped": self._dropped[TraceLevel.AUDIT],
                "trace_dropped": self._dropped[TraceLevel.TRACE],
                "operational_dropped": self._dropped[TraceLevel.OPERATIONAL],
            }
