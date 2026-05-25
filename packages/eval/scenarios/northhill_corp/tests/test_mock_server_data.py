import json
import shutil
import tempfile
from pathlib import Path

import pytest
from scenarios.northhill_corp.seed import main as seed_northhill


@pytest.fixture
def northhill_root():
    td = Path(tempfile.mkdtemp(prefix="mock-nh-"))
    try:
        seed_northhill(td, clean=True)
        yield td
    finally:
        shutil.rmtree(td, ignore_errors=True)


class TestMockServerFinance:
    def test_expenses_loaded(self, northhill_root):
        expenses = []
        for status in ("pending", "approved", "rejected"):
            d = northhill_root / "finance" / "expenses" / status
            if d.exists():
                for f in sorted(d.glob("*.json")):
                    expenses.append(json.loads(f.read_text()))
        assert len(expenses) >= 3, f"Expected >=3 expenses, got {len(expenses)}"
        for exp in expenses:
            assert "expense_id" in exp
            assert "amount" in exp
            assert "status" in exp

    def test_purchase_orders_loaded(self, northhill_root):
        pos = []
        for status in ("open", "approved", "received"):
            d = northhill_root / "finance" / "purchase_orders" / status
            if d.exists():
                for f in sorted(d.glob("*.json")):
                    pos.append(json.loads(f.read_text()))
        assert len(pos) >= 2

    def test_invoices_loaded(self, northhill_root):
        invoices = []
        for status in ("pending", "paid", "disputed"):
            d = northhill_root / "finance" / "invoices" / status
            if d.exists():
                for f in sorted(d.glob("*.json")):
                    invoices.append(json.loads(f.read_text()))
        assert len(invoices) >= 2

    def test_budgets_loaded(self, northhill_root):
        budget_file = northhill_root / "finance" / "budgets" / "Q2_2026.json"
        assert budget_file.exists()
        budgets = json.loads(budget_file.read_text())
        assert isinstance(budgets, dict)
        assert "departments" in budgets


class TestMockServerCustomers:
    def test_accounts_loaded(self, northhill_root):
        accts_dir = northhill_root / "customers" / "accounts"
        assert accts_dir.exists()
        accounts = [json.loads(f.read_text()) for f in sorted(accts_dir.glob("*.json"))]
        assert len(accounts) >= 3
        for acct in accounts:
            assert "account_id" in acct

    def test_escalations_loaded(self, northhill_root):
        esc_dir = northhill_root / "customers" / "escalations"
        assert esc_dir.exists()
        escalations = [json.loads(f.read_text()) for f in sorted(esc_dir.glob("*.json"))]
        assert len(escalations) >= 2
        for esc in escalations:
            assert "escalation_id" in esc


class TestMockServerCompliance:
    def test_contracts_loaded(self, northhill_root):
        contracts = []
        for status in ("in_review", "active", "expired"):
            d = northhill_root / "compliance" / "contracts" / status
            if d.exists():
                for f in sorted(d.glob("*.json")):
                    contracts.append(json.loads(f.read_text()))
        assert len(contracts) >= 3

    def test_audits_loaded(self, northhill_root):
        audits_dir = northhill_root / "compliance" / "audits"
        assert audits_dir.exists()
        audits = [json.loads(f.read_text()) for f in sorted(audits_dir.glob("*.json"))]
        assert len(audits) >= 1
        for audit in audits:
            assert "audit_id" in audit

    def test_policies_loaded(self, northhill_root):
        policies_dir = northhill_root / "compliance" / "policies"
        assert policies_dir.exists()
        policies = [json.loads(f.read_text()) for f in sorted(policies_dir.glob("*.json"))]
        assert len(policies) >= 1


class TestMockServerDataIntegrity:
    def test_expense_status_values(self, northhill_root):
        """All expenses should have valid status values."""
        valid_statuses = {"pending", "approved", "rejected"}
        for status_dir in ("pending", "approved", "rejected"):
            d = northhill_root / "finance" / "expenses" / status_dir
            if d.exists():
                for f in d.glob("*.json"):
                    data = json.loads(f.read_text())
                    assert data["status"] in valid_statuses, (
                        f"{f.name} has invalid status: {data['status']}"
                    )
                    assert data["status"] == status_dir, (
                        f"{f.name} status {data['status']} doesn't match dir {status_dir}"
                    )

    def test_account_health_scores_in_range(self, northhill_root):
        """Health scores should be between 0 and 100."""
        accts_dir = northhill_root / "customers" / "accounts"
        for f in accts_dir.glob("*.json"):
            data = json.loads(f.read_text())
            score = data.get("health_score", 0)
            assert 0 <= score <= 100, (
                f"{f.name} health_score {score} out of range"
            )

    def test_escalation_references_valid_account(self, northhill_root):
        """Escalations should reference existing account IDs."""
        accts_dir = northhill_root / "customers" / "accounts"
        account_ids = set()
        for f in accts_dir.glob("*.json"):
            data = json.loads(f.read_text())
            account_ids.add(data["account_id"])

        esc_dir = northhill_root / "customers" / "escalations"
        for f in esc_dir.glob("*.json"):
            data = json.loads(f.read_text())
            ref = data.get("account_id")
            if ref:
                assert ref in account_ids, (
                    f"Escalation {f.name} references non-existent account {ref}"
                )
