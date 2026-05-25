from mirage.resource.disk import DiskResource

PROMPT = """\
{prefix}
  northhill-data/                              — primary data bucket
    logs/platform-api/2026/05/<DD>/app.log     — daily application logs (text)
    exports/monthly/2026-04-customers.csv      — monthly customer data export
    exports/monthly/2026-04-revenue.csv        — monthly revenue export
    backups/db/2026-05-14-platform-db.sql.meta — database backup metadata
    artifacts/deployments/<version>/build.log  — deployment build logs
    reports/quarterly/Q1-2026-board-deck.meta  — quarterly report metadata

  Log format (one line per entry):
    <timestamp> <level> [<service>] <message>

  Listing helpers:
    ls   {prefix}/northhill-data/logs/platform-api/2026/05/
    cat  {prefix}/northhill-data/logs/platform-api/2026/05/15/app.log
    cat  {prefix}/northhill-data/exports/monthly/2026-04-customers.csv
    cat  {prefix}/northhill-data/artifacts/deployments/v3.18.7/build.log"""

WRITE_PROMPT = ""


class FakeS3Resource(DiskResource):
    PROMPT: str = PROMPT
    WRITE_PROMPT: str = WRITE_PROMPT
