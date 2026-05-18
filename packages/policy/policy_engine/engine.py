from __future__ import annotations

import logging
from typing import Any

from policy_engine.acl import AccessDecision, ColumnAcl

logger = logging.getLogger(__name__)


class PolicyEngine:
    """Evaluates access policies at the FUSE boundary.

    When the agent reads a column, the policy engine determines whether
    access is allowed, denied, or filtered.  Enforcement is structural:
    denied data physically cannot reach the agent.
    """

    def __init__(self) -> None:
        self._acls: dict[str, ColumnAcl] = {}

    def register_acl(self, source: str, table: str, acl: ColumnAcl) -> None:
        """Register column-level ACL for a source table.

        Args:
            source (str): Data source identifier.
            table (str): Table name.
            acl (ColumnAcl): Access control list.
        """
        self._acls[f"{source}/{table}"] = acl

    def evaluate(self, source: str, table: str, columns: list[str]) -> AccessDecision:
        """Evaluate access for specific columns.

        Args:
            source (str): Data source identifier.
            table (str): Table name.
            columns (list[str]): Requested columns.
        """
        key = f"{source}/{table}"
        acl = self._acls.get(key)
        if acl is None:
            return AccessDecision(allowed=columns, denied=[], row_filter=None)
        return acl.evaluate(columns)

    def check_budget(self, session_id: str, estimated_rows: int) -> bool:
        """Check whether a query is within the session's compute budget.

        Args:
            session_id (str): Agent session identifier.
            estimated_rows (int): Estimated rows to scan.
        """
        raise NotImplementedError
