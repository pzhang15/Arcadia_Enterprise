from mirage.resource.disk import DiskResource

PROMPT = """\
{prefix}
  tables/                         — list of available tables
  tables/<table>/schema.json      — column names, types, constraints
  tables/<table>/data.jsonl       — rows as JSON lines (one object per line)
  tables/<table>/stats.json       — row count, size estimate, last updated

  Available tables: users, events, subscriptions, invoices

  Schema JSON shape:
    {{"table": "...",
      "columns": [{{"name": "...", "type": "...",
        "nullable": bool, "primary_key": bool}}],
      "foreign_keys": [...]}}

  Stats JSON shape:
    {{"table": "...", "row_count": N, "size_bytes": N, "last_updated": "..."}}

  Listing helpers:
    ls   {prefix}/tables/
    cat  {prefix}/tables/users/schema.json
    cat  {prefix}/tables/subscriptions/data.jsonl
    jq  '.columns[] | .name' {prefix}/tables/invoices/schema.json"""

WRITE_PROMPT = ""


class FakePostgresResource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT
