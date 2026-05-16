from mirage.resource.disk import DiskResource

PROMPT = """\
{prefix}
  logs/<service>/
    <date>.jsonl          # one JSON object per log line
  metrics/<service>/
    <metric-name>.json    # time-series points array

  Log entry shape (one per line in .jsonl):
    {{"timestamp": "...", "service": "...", "level": "ERROR|WARN|INFO",
      "message": "...", "attributes": {{...}}}}

  Metric JSON shape:
    {{"metric": "...", "unit": "...",
      "points": [["<iso-ts>", <value>], ...],
      "tags": ["service:...", ...]}}

  Listing helpers:
    ls   {prefix}/logs/payments-api/
    cat  {prefix}/logs/payments-api/2026-05-15.jsonl
    jq  '.points' {prefix}/metrics/payments-api/latency_p99.json"""

WRITE_PROMPT = ""


class FakeDatadogResource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT
