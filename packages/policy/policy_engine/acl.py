from __future__ import annotations

from pydantic import BaseModel


class AccessDecision(BaseModel):
    """Result of evaluating column access against an ACL."""

    allowed: list[str]
    denied: list[str]
    row_filter: str | None = None


class ColumnAcl:
    """Column-level access control list for a single table.

    Specifies which columns are allowed, denied, or require masking
    for a given agent/task context.
    """

    def __init__(
        self,
        denied_columns: list[str] | None = None,
        row_filter: str | None = None,
    ) -> None:
        self._denied = set(denied_columns or [])
        self._row_filter = row_filter

    def evaluate(self, requested: list[str]) -> AccessDecision:
        """Determine access for a set of requested columns.

        Args:
            requested (list[str]): Column names the agent wants to read.
        """
        allowed = [c for c in requested if c not in self._denied]
        denied = [c for c in requested if c in self._denied]
        return AccessDecision(
            allowed=allowed,
            denied=denied,
            row_filter=self._row_filter,
        )
