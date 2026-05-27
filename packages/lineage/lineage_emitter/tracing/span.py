from __future__ import annotations

import enum
import time
import uuid
from dataclasses import dataclass, field


class TraceLevel(enum.IntEnum):
    AUDIT = 0
    TRACE = 1
    OPERATIONAL = 2


class SpanKind(enum.IntEnum):
    ROOT = 0
    INTERNAL = 1
    CLIENT = 2


class SpanStatus(enum.IntEnum):
    OK = 0
    ERROR = 1


@dataclass
class SpanEvent:
    """A timestamped annotation attached to a span.

    Args:
        timestamp_ms (int): UTC epoch milliseconds.
        name (str): Event name.
        attributes (dict[str, str | int | float | bool]): Event metadata.
    """

    timestamp_ms: int
    name: str
    attributes: dict[str,
                     str | int | float | bool] = field(default_factory=dict)


@dataclass
class SpanMetrics:
    """Aggregate I/O metrics for a span.

    Args:
        bytes_read (int): Total bytes read.
        bytes_written (int): Total bytes written.
        api_calls (int): Number of backing API calls triggered.
        cache_hits (int): Number of cache hits.
        cache_misses (int): Number of cache misses.
    """

    bytes_read: int = 0
    bytes_written: int = 0
    api_calls: int = 0
    cache_hits: int = 0
    cache_misses: int = 0


@dataclass
class Span:
    """An OTel-compatible hierarchical trace span.

    Args:
        trace_id (str): UUID shared across all spans in one execute() call.
        span_id (str): UUID unique to this span.
        parent_span_id (str | None): Parent span UUID, None for root spans.
        name (str): Span name (e.g. "execute", "read", "write").
        kind (SpanKind): ROOT, INTERNAL, or CLIENT.
        start_time_ms (int): UTC epoch milliseconds when span started.
        end_time_ms (int): UTC epoch milliseconds when span ended. 0 if still open.
        status (SpanStatus): OK or ERROR.
        attributes (dict[str, str | int | float | bool]): Span metadata.
        events (list[SpanEvent]): Timestamped annotations.
        metrics (SpanMetrics): Aggregate I/O metrics.
        level (TraceLevel): Priority tier for ring buffer eviction.
        session_id (str): Agent session identifier.
        agent_id (str): Agent identifier.
    """

    trace_id: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    parent_span_id: str | None = None
    name: str = ""
    kind: SpanKind = SpanKind.INTERNAL
    start_time_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    end_time_ms: int = 0
    status: SpanStatus = SpanStatus.OK
    attributes: dict[str,
                     str | int | float | bool] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)
    metrics: SpanMetrics = field(default_factory=SpanMetrics)
    level: TraceLevel = TraceLevel.TRACE
    session_id: str = ""
    agent_id: str = ""

    @property
    def duration_ms(self) -> int:
        if self.end_time_ms == 0:
            return 0
        return self.end_time_ms - self.start_time_ms

    def finish(self, status: SpanStatus = SpanStatus.OK) -> None:
        """Mark this span as finished with the current timestamp.

        Args:
            status (SpanStatus): Final status for this span.
        """
        self.end_time_ms = int(time.time() * 1000)
        self.status = status

    def add_event(
            self,
            name: str,
            attributes: dict[str, str | int | float | bool] | None = None
    ) -> None:
        """Attach a timestamped event to this span.

        Args:
            name (str): Event name.
            attributes (dict[str, str | int | float | bool] | None): Event metadata.
        """
        self.events.append(
            SpanEvent(
                timestamp_ms=int(time.time() * 1000),
                name=name,
                attributes=attributes or {},
            ))
