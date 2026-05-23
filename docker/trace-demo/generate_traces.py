import asyncio
import sys
from pathlib import Path

from mirage import MountMode, RAMResource, Workspace

from lineage_emitter.tracing.config import TraceConfig
from lineage_emitter.workspace import TracingWorkspace

DB_PATH = Path("/app/data/traces.db")

DEMO_COMMANDS = [
    ("echo 'Incident INC-5521: Payment gateway timeout' > /data/incident.txt", "Write incident report"),
    ("echo '{\"severity\": \"high\", \"service\": \"payments-api\"}' > /data/incident_meta.json", "Write incident metadata"),
    ("echo 'Connection pool exhaustion detected at 14:32 UTC' > /data/app_log.txt", "Write application logs"),
    ("echo 'p99 latency spiked to 12s at 14:30 UTC' > /data/metrics_log.txt", "Write metrics log"),
    ("echo 'Deploy d4e5f6 rolled back at 14:45 UTC' > /data/deploy_log.txt", "Write deploy log"),
    ("cat /data/incident.txt", "Read incident report"),
    ("cat /data/incident_meta.json", "Read incident metadata"),
    ("cat /data/app_log.txt", "Read application logs"),
    ("cat /data/metrics_log.txt", "Read metrics log"),
    ("cat /data/deploy_log.txt", "Read deploy log"),
    ("grep timeout /data/incident.txt", "Search for timeout"),
    ("wc -l /data/app_log.txt", "Count log lines"),
    ("echo 'Root cause: pool max_size=10, load spike to 500 req/s' > /data/root_cause.txt", "Write root cause"),
    ("cat /data/root_cause.txt", "Read root cause"),
    ("cat /data/nonexistent.txt", "Read missing file (error case)"),
    ("echo 'Remediation: increase pool to 50, add breaker' > /data/remediation.txt", "Write remediation"),
    ("cat /data/remediation.txt", "Read remediation plan"),
    ("ls /data/", "List all workspace files"),
    ("cat /data/incident.txt", "Re-read incident (cache test)"),
    ("cat /data/app_log.txt", "Re-read app log (cache test)"),
]


async def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    config = TraceConfig(
        db_path=str(DB_PATH),
        flush_interval_seconds=1.0,
    )

    ws = Workspace(
        {"/data": RAMResource()},
        mode=MountMode.WRITE,
    )
    tw = TracingWorkspace(ws, config)
    tw.start()

    print(f"Generating {len(DEMO_COMMANDS)} traces -> {DB_PATH}")

    for i, (cmd, desc) in enumerate(DEMO_COMMANDS):
        result = await tw.execute(cmd, agent_id="demo-agent")
        status = "OK" if result.exit_code == 0 else "ERR"
        print(f"  [{i+1:2d}/{len(DEMO_COMMANDS)}] {status} {desc}")
        await asyncio.sleep(0.05)

    await tw.stop()
    tw.flush_sync()

    span_count = tw.store.count_spans() if tw.store else 0
    trace_count = tw.store.count_spans(level=0) if tw.store else 0
    print(f"\nDone: {trace_count} traces, {span_count} total spans written to {DB_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
