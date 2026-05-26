import json

import pytest

ALL_MOUNTS = (
    "slack",
    "sheets",
    "gdocs",
    "tickets",
    "github",
    "pagerduty",
    "datadog",
    "finance",
    "customers",
    "compliance",
    "database",
    "s3",
)


class TestMountDiscovery:
    """All 13 mounts (12 service + RAM root) are visible."""

    @pytest.mark.asyncio
    async def test_ls_root_lists_all_mounts(self, l1_workspace):
        result = await l1_workspace.execute("ls /")
        assert result.exit_code == 0
        stdout = result.stdout.decode()
        for mount in ALL_MOUNTS:
            assert mount in stdout, f"Mount /{mount} missing from ls /"


class TestDatabaseMount:
    """Postgres-like /database mount is readable and correct."""

    @pytest.mark.asyncio
    async def test_list_tables(self, l1_workspace):
        result = await l1_workspace.execute("ls /database/tables/")
        assert result.exit_code == 0
        stdout = result.stdout.decode()
        for table in ("users", "events", "subscriptions", "invoices"):
            assert table in stdout

    @pytest.mark.asyncio
    async def test_read_schema(self, l1_workspace):
        result = await l1_workspace.execute(
            "cat /database/tables/users/schema.json")
        assert result.exit_code == 0
        schema = json.loads(result.stdout.decode())
        assert schema["table"] == "users"
        col_names = [c["name"] for c in schema["columns"]]
        assert "user_id" in col_names
        assert "account_id" in col_names

    @pytest.mark.asyncio
    async def test_read_stats(self, l1_workspace):
        result = await l1_workspace.execute(
            "cat /database/tables/events/stats.json")
        assert result.exit_code == 0
        stats = json.loads(result.stdout.decode())
        assert stats["row_count"] == 5000

    @pytest.mark.asyncio
    async def test_query_subscriptions(self, l1_workspace):
        result = await l1_workspace.execute(
            "cat /database/tables/subscriptions/data.jsonl")
        assert result.exit_code == 0
        lines = result.stdout.decode().strip().split("\n")
        assert len(lines) >= 50
        first = json.loads(lines[0])
        assert "subscription_id" in first
        assert "account_id" in first
        assert "mrr" in first


class TestS3Mount:
    """S3-like /s3 mount is readable and cross-referenced."""

    @pytest.mark.asyncio
    async def test_list_bucket(self, l1_workspace):
        result = await l1_workspace.execute("ls /s3/northhill-data/")
        assert result.exit_code == 0
        stdout = result.stdout.decode()
        for d in ("logs", "exports", "artifacts", "backups", "reports"):
            assert d in stdout

    @pytest.mark.asyncio
    async def test_read_build_log(self, l1_workspace):
        path = ("/s3/northhill-data/artifacts/"
                "deployments/v3.18.7/build.log")
        result = await l1_workspace.execute(f"cat {path}")
        assert result.exit_code == 0
        content = result.stdout.decode()
        assert "f3a1b2c8" in content
        assert "frank.osei" in content
        assert "d4e5f6" in content

    @pytest.mark.asyncio
    async def test_read_daily_log(self, l1_workspace):
        path = ("/s3/northhill-data/logs/"
                "platform-api/2026/05/15/app.log")
        result = await l1_workspace.execute(f"cat {path}")
        assert result.exit_code == 0
        lines = result.stdout.decode().strip().split("\n")
        assert len(lines) >= 50

    @pytest.mark.asyncio
    async def test_read_customer_csv(self, l1_workspace):
        path = ("/s3/northhill-data/exports/"
                "monthly/2026-04-customers.csv")
        result = await l1_workspace.execute(f"cat {path}")
        assert result.exit_code == 0
        content = result.stdout.decode()
        assert "ACCT-1001" in content
        assert "GlobalTech" in content


class TestCrossSystemCorrelation:
    """Validate that cross-references work end-to-end."""

    @pytest.mark.asyncio
    async def test_incident_to_deployment(self, l1_workspace):
        """INC-5521 links to deployment d4e5f6."""
        inc = await l1_workspace.execute(
            "cat /pagerduty/incidents/triggered/INC-5521.json")
        assert inc.exit_code == 0
        data = json.loads(inc.stdout.decode())
        assert "d4e5f6" in json.dumps(data)

        deploy = await l1_workspace.execute(
            "cat /github/repos/northhill/"
            "platform-api/deployments/d4e5f6.json")
        assert deploy.exit_code == 0
        deploy_data = json.loads(deploy.stdout.decode())
        assert "f3a1b2c8" in json.dumps(deploy_data)

    @pytest.mark.asyncio
    async def test_customer_to_escalation(self, l1_workspace):
        """GlobalTech ACCT-1001 has escalation ESC-1001."""
        acct = await l1_workspace.execute(
            "cat /customers/accounts/ACCT-1001.json")
        assert acct.exit_code == 0
        acct_data = json.loads(acct.stdout.decode())
        assert acct_data["health_score"] == 45

        esc = await l1_workspace.execute(
            "cat /customers/escalations/ESC-1001.json")
        assert esc.exit_code == 0
        esc_data = json.loads(esc.stdout.decode())
        assert esc_data["account_id"] == "ACCT-1001"
        assert "INC-5521" in esc_data.get("linked_incidents", [])

    @pytest.mark.asyncio
    async def test_database_subscription_references_account(
        self,
        l1_workspace,
    ):
        """Database subscriptions FK to real customer accounts."""
        subs = await l1_workspace.execute(
            "cat /database/tables/subscriptions/data.jsonl")
        assert subs.exit_code == 0

        accts = await l1_workspace.execute("ls /customers/accounts/")
        assert accts.exit_code == 0
        acct_files = accts.stdout.decode().strip().split("\n")
        account_ids = set()
        for fname in acct_files:
            fname = fname.strip()
            if fname.endswith(".json"):
                aid = fname.replace(".json", "")
                account_ids.add(aid)

        for line in subs.stdout.decode().strip().split("\n")[:10]:
            row = json.loads(line)
            assert row["account_id"] in account_ids, (
                f"Subscription {row['subscription_id']} references "
                f"unknown account {row['account_id']}")

    @pytest.mark.asyncio
    async def test_s3_build_log_matches_github_commit(
        self,
        l1_workspace,
    ):
        """S3 build log references same commit as GitHub."""
        build = await l1_workspace.execute("cat /s3/northhill-data/artifacts/"
                                           "deployments/v3.18.7/build.log")
        assert build.exit_code == 0
        build_text = build.stdout.decode()

        commit = await l1_workspace.execute(
            "cat /github/repos/northhill/"
            "platform-api/commits/f3a1b2c8.json")
        assert commit.exit_code == 0
        commit_data = json.loads(commit.stdout.decode())

        assert commit_data["sha"].startswith("f3a1b2c8")
        assert "f3a1b2c8" in build_text

    @pytest.mark.asyncio
    async def test_datadog_metrics_spike_at_incident_time(
        self,
        l1_workspace,
    ):
        """Datadog metrics show spike at 14:00 matching INC-5521."""
        result = await l1_workspace.execute(
            "cat /datadog/metrics/platform-api/p99_latency.json")
        assert result.exit_code == 0
        data = json.loads(result.stdout.decode())
        points = {ts: val for ts, val in data["points"]}
        assert points["2026-05-15T14:00:00Z"] > 2000


class TestAmbientNoise:
    """Slack channels contain ambient noise messages."""

    @pytest.mark.asyncio
    async def test_channels_have_many_messages(self, l1_workspace):
        result = await l1_workspace.execute(
            "find /slack/channels -name 'chat.jsonl' -type f")
        assert result.exit_code == 0
        files = result.stdout.decode().strip().split("\n")
        assert len(files) >= 20, ("Expected many chat.jsonl files across "
                                  "channels and dates")

    @pytest.mark.asyncio
    async def test_user_profiles_include_generated(
        self,
        l1_workspace,
    ):
        result = await l1_workspace.execute("ls /slack/users/ | wc -l")
        assert result.exit_code == 0
        count = int(result.stdout.decode().strip())
        assert count >= 100, (f"Expected >=100 user profiles, got {count}")


class TestAgentOutputWorkflow:
    """Agent can write output files and read them back."""

    @pytest.mark.asyncio
    async def test_write_report_and_verify(self, l1_workspace):
        """Simulates an agent writing a report file."""
        report = "# Risk Report\\nACCT-1001 GlobalTech: at risk"
        cmd = f'echo "{report}" > /risk_report.md'
        result = await l1_workspace.execute(cmd)
        assert result.exit_code == 0

        read = await l1_workspace.execute("cat /risk_report.md")
        assert read.exit_code == 0
        content = read.stdout.decode()
        assert "GlobalTech" in content
        assert "ACCT-1001" in content

    @pytest.mark.asyncio
    async def test_find_incident_in_slack(self, l1_workspace):
        """Agent can find INC-5521 in incident channel."""
        path = "/slack/channels/incidents__C305"
        result = await l1_workspace.execute(
            f"find {path} -name 'chat.jsonl' -type f")
        assert result.exit_code == 0
        files = result.stdout.decode().strip().split("\n")
        found = False
        for f in files:
            f = f.strip()
            if not f:
                continue
            cat = await l1_workspace.execute(f"cat {f}")
            if b"INC-5521" in cat.stdout:
                found = True
                break
        assert found, "INC-5521 not found in incidents channel"
