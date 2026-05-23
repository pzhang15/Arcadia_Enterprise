from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TraceConfig:
    """Configuration for the tracing system.

    Args:
        buffer_capacity_audit (int): Ring buffer capacity for AUDIT spans.
        buffer_capacity_trace (int): Ring buffer capacity for TRACE spans.
        buffer_capacity_operational (int): Ring buffer capacity for OPERATIONAL spans.
        flush_interval_seconds (float): How often the background flusher drains the buffer.
        db_path (str | None): Path to SQLite database file. None disables persistence.
        emit_level (int): Minimum TraceLevel ordinal to emit. 0=AUDIT, 1=TRACE, 2=OPERATIONAL.
        flight_recorder_seconds (float): Seconds of OPERATIONAL spans to retain in memory
            for retroactive dump on error, even when emit_level < OPERATIONAL.
    """

    buffer_capacity_audit: int = 10_000
    buffer_capacity_trace: int = 50_000
    buffer_capacity_operational: int = 100_000
    flush_interval_seconds: float = 5.0
    db_path: str | None = None
    emit_level: int = 1
    flight_recorder_seconds: float = 300.0
