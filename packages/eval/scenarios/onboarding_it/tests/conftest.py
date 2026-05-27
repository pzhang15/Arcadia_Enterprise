import shutil
import tempfile
from pathlib import Path

import pytest
from scenarios.onboarding_it import seed
from scenarios.onboarding_it.mounts import build_l1_workspace


@pytest.fixture
def disk_root() -> Path:
    """A fresh on-disk corpus for the test, wiped on teardown."""
    td = Path(tempfile.mkdtemp(prefix="mirage-eval-test-"))
    try:
        seed.main(td, clean=True)
        yield td
    finally:
        shutil.rmtree(td, ignore_errors=True)


@pytest.fixture
def l1_workspace(disk_root):
    return build_l1_workspace(disk_root=disk_root, session_id="default")
