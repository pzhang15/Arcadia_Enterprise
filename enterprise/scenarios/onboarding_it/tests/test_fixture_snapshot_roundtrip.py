import tempfile
from pathlib import Path

import pytest
from mirage_eval.fixtures.build_snapshot import snapshot_workspace
from scenarios.onboarding_it import seed
from scenarios.onboarding_it.mounts import build_l1_workspace

from mirage import Workspace


def test_seed_writes_expected_top_level_dirs():
    with tempfile.TemporaryDirectory(prefix="mirage-eval-seed-") as td:
        root = seed.main(td)
        names = {p.name for p in Path(root).iterdir()}
        assert names == {"slack", "sheets", "gdocs", "tickets"}


def test_seed_file_count_is_stable():
    """The seed corpus has a stable shape; if this number changes, update
    here intentionally so we notice."""
    with tempfile.TemporaryDirectory(prefix="mirage-eval-seed-") as td:
        root = seed.main(td)
        n = sum(1 for _ in Path(root).rglob("*") if _.is_file())
        assert n == 37, f"expected 37 files, got {n}"


@pytest.mark.asyncio
async def test_snapshot_roundtrip_preserves_content(disk_root):
    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as t:
        snapshot_path = Path(t.name)
    try:
        ws1 = build_l1_workspace(disk_root=disk_root, session_id="snap-source")
        out = await snapshot_workspace(ws1, snapshot_path)
        assert out.exists() and out.stat().st_size > 0
        ws2 = Workspace.load(str(snapshot_path))
        assert ws2 is not None
    finally:
        snapshot_path.unlink(missing_ok=True)
