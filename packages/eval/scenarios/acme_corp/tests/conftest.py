import shutil
import tempfile
from pathlib import Path

import pytest
from scenarios.acme_corp import seed
from scenarios.acme_corp.mounts import build_l1_workspace


@pytest.fixture
def disk_root() -> Path:
    td = Path(tempfile.mkdtemp(prefix="mirage-eval-acme-"))
    try:
        seed.main(td, clean=True)
        yield td
    finally:
        shutil.rmtree(td, ignore_errors=True)


@pytest.fixture
def l1_workspace(disk_root):
    return build_l1_workspace(disk_root=disk_root, session_id="default")
