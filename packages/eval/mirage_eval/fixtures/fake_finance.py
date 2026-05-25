from mirage.resource.disk import DiskResource

PROMPT = (
    "Financial data mounted from an internal finance system.\n\n"
    "Layout:\n"
    "  expenses/{pending,approved,rejected}/EXP-XXXX.json\n"
    "    Each file: expense_id, submitter, department, amount, currency,\n"
    "    category, description, receipt_url, submitted_at, status,\n"
    "    approver, line_items\n"
    "  purchase_orders/{open,approved,received}/PO-XXXX.json\n"
    "    Each file: po_id, requester, vendor, items, total, status,\n"
    "    created_at, approved_by, department\n"
    "  invoices/{pending,paid,disputed}/INV-XXXX.json\n"
    "    Each file: invoice_id, vendor, amount, due_date, po_reference,\n"
    "    status, department\n"
    "  budgets/Q2_2026.json\n"
    "    Department budget breakdowns with spend-to-date\n\n"
    "Use ls, cat, jq to browse. Amounts are in USD.")

WRITE_PROMPT = ""


class FakeFinanceResource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT
