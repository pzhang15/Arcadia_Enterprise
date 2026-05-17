import shutil
import tempfile
from pathlib import Path

import pytest

from scenarios.meridian_labs import seed
from scenarios.meridian_labs.mounts import build_l1_workspace


@pytest.fixture
def disk_root() -> Path:
    td = Path(tempfile.mkdtemp(prefix="mirage-eval-ml-"))
    try:
        seed.main(td, clean=True)
        yield td
    finally:
        shutil.rmtree(td, ignore_errors=True)


@pytest.fixture
def l1_workspace(disk_root):
    return build_l1_workspace(disk_root=disk_root, session_id="default")
