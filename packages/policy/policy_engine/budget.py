from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class BudgetTracker:
    """Tracks compute budget consumption per agent session.

    Enforces scan limits (max rows), query count limits, and
    cost ceilings to prevent runaway agent data access.
    """

    def __init__(self, max_rows: int = 1_000_000, max_queries: int = 100) -> None:
        self._max_rows = max_rows
        self._max_queries = max_queries
        self._sessions: dict[str, _SessionBudget] = {}

    def check(self, session_id: str, estimated_rows: int) -> bool:
        """Return True if the query is within budget.

        Args:
            session_id (str): Agent session identifier.
            estimated_rows (int): Estimated row count for the query.
        """
        budget = self._sessions.setdefault(
            session_id,
            _SessionBudget(max_rows=self._max_rows, max_queries=self._max_queries),
        )
        return budget.can_execute(estimated_rows)

    def record(self, session_id: str, actual_rows: int) -> None:
        """Record a completed query's row consumption.

        Args:
            session_id (str): Agent session identifier.
            actual_rows (int): Actual rows scanned.
        """
        budget = self._sessions.get(session_id)
        if budget:
            budget.record(actual_rows)


class _SessionBudget:
    def __init__(self, max_rows: int, max_queries: int) -> None:
        self.max_rows = max_rows
        self.max_queries = max_queries
        self.rows_used = 0
        self.queries_used = 0

    def can_execute(self, estimated_rows: int) -> bool:
        if self.queries_used >= self.max_queries:
            return False
        if self.rows_used + estimated_rows > self.max_rows:
            return False
        return True

    def record(self, actual_rows: int) -> None:
        self.rows_used += actual_rows
        self.queries_used += 1
