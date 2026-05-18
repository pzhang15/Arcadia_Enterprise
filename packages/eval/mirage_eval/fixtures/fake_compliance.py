from mirage.resource.disk import DiskResource

PROMPT = (
    "Legal and compliance data.\n\n"
    "Layout:\n"
    "  contracts/{in_review,active,expired}/CTR-XXXX.json\n"
    "    Each file: contract_id, counterparty, type, value,\n"
    "    start_date, end_date, status, owner, review_notes\n"
    "  audits/AUDIT-XXXX.json\n"
    "    Each file: audit_id, framework, status, due_date,\n"
    "    checklist (list of items with name, status, owner, evidence_link)\n"
    "  policies/POL-XXXX.json\n"
    "    Each file: policy_id, title, version, effective_date,\n"
    "    acknowledgments (list with user_id, acked_at)\n\n"
    "Contract types: NDA, MSA, SOW. Frameworks: SOC2, GDPR, HIPAA."
)

WRITE_PROMPT = ""


class FakeComplianceResource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT
