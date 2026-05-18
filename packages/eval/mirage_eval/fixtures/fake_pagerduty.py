from mirage.resource.disk import DiskResource

PROMPT = """\
{prefix}
  services/<service-id>.json
  incidents/
    triggered/<incident-id>.json
    acknowledged/<incident-id>.json
    resolved/<incident-id>.json

  Service JSON: id, name, description, status, escalation_policy, teams[].
  Incident JSON: id, title, status, urgency, severity.value, service,
    created_at, assignments[], acknowledgements[], body.details.

  Listing helpers:
    ls   {prefix}/incidents/triggered/
    cat  {prefix}/incidents/triggered/INC-5521.json
    jq  '.service.name' {prefix}/incidents/triggered/*.json"""

WRITE_PROMPT = ""


class FakePagerDutyResource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT
