from mirage.resource.disk import DiskResource

PROMPT = (
    "Customer data from CRM and support systems.\n\n"
    "Layout:\n"
    "  accounts/ACCT-XXXX.json\n"
    "    Each file: account_id, company_name, tier, arr, health_score,\n"
    "    csm, renewal_date, contacts, products\n"
    "  escalations/ESC-XXXX.json\n"
    "    Each file: escalation_id, account_id, severity, description,\n"
    "    linked_ticket, created_at, status, owner\n\n"
    "Health scores: 0-100 (>80 healthy, 60-80 needs attention, <60 at risk).\n"
    "Tiers: enterprise, pro, starter."
)

WRITE_PROMPT = ""


class FakeCustomersResource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT
