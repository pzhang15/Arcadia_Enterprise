import pytest

from mirage import MountMode, RAMResource, Workspace
from mirage.observe.record import OpRecord


@pytest.fixture()
def workspace():
    return Workspace({"/data": RAMResource()}, mode=MountMode.WRITE)


@pytest.mark.asyncio
async def test_ops_property_exists(workspace):
    """Workspace.ops is a public property returning an Ops instance."""
    ops = workspace.ops
    assert ops is not None
    assert hasattr(ops, "records")


@pytest.mark.asyncio
async def test_ops_records_is_list(workspace):
    """Workspace.ops.records is a list that starts empty."""
    records = workspace.ops.records
    assert isinstance(records, list)


@pytest.mark.asyncio
async def test_ops_records_populated_after_execute(workspace):
    """After execute(), ops.records contains OpRecord instances."""
    await workspace.execute("echo hello > /data/test.txt")
    await workspace.execute("cat /data/test.txt")

    records = workspace.ops.records
    assert len(records) > 0
    for rec in records:
        assert isinstance(rec, OpRecord)


@pytest.mark.asyncio
async def test_ops_records_cumulative(workspace):
    """ops.records accumulates across multiple execute() calls."""
    await workspace.execute("echo a > /data/a.txt")
    count_after_first = len(workspace.ops.records)

    await workspace.execute("echo b > /data/b.txt")
    count_after_second = len(workspace.ops.records)

    assert count_after_second > count_after_first


@pytest.mark.asyncio
async def test_ops_records_snapshot_and_slice(workspace):
    """Snapshot-and-slice pattern yields per-call records."""
    await workspace.execute("echo a > /data/a.txt")
    offset = len(workspace.ops.records)

    await workspace.execute("cat /data/a.txt")
    new_records = workspace.ops.records[offset:]

    assert len(new_records) > 0
    assert all(isinstance(r, OpRecord) for r in new_records)


@pytest.mark.asyncio
async def test_op_record_fields(workspace):
    """OpRecord has the fields TracingWorkspace depends on."""
    await workspace.execute("echo test > /data/fields.txt")
    await workspace.execute("cat /data/fields.txt")

    for rec in workspace.ops.records:
        assert hasattr(rec, "op")
        assert hasattr(rec, "path")
        assert hasattr(rec, "source")
        assert hasattr(rec, "bytes")
        assert hasattr(rec, "timestamp")
        assert hasattr(rec, "duration_ms")
        assert hasattr(rec, "mount_prefix")
        assert hasattr(rec, "fingerprint")
        assert hasattr(rec, "revision")
        assert hasattr(rec, "is_cache")
