"""Guard: the pure framework modules must not import mirage at module load.

The dev venv HAS mirage installed, so an in-process ``"mirage" not in
sys.modules`` check is unreliable. Each pure module is therefore imported in a
SUBPROCESS whose meta-path is rigged so any ``import mirage`` (or submodule)
raises ``ModuleNotFoundError``. If the module imports cleanly there AND leaves
no ``mirage`` key in ``sys.modules``, it is genuinely mirage-free at load time.
``adapters`` is intentionally excluded — it is the one runtime mirage seam.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

PURE_MODULES = [
    "mirage_dstest.clock",
    "mirage_dstest.rng",
    "mirage_dstest.modelfs",
    "mirage_dstest.protocols",
    "mirage_dstest.statemachine",
    "mirage_dstest.chaos",
    "mirage_dstest.history",
    "mirage_dstest.contract",
    "mirage_dstest",
]

_SUBPROCESS_TEMPLATE = """
import sys


class _BlockMirage:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "mirage" or fullname.startswith("mirage."):
            raise ModuleNotFoundError("blocked mirage import: " + fullname)
        return None


sys.meta_path.insert(0, _BlockMirage())
import importlib
importlib.import_module({module!r})
assert "mirage" not in sys.modules, (
    "module {module!r} pulled mirage into sys.modules: "
    + repr([m for m in sys.modules if m == "mirage" or m.startswith("mirage.")])
)
print("OK")
"""


@pytest.mark.parametrize("module", PURE_MODULES)
def test_pure_module_imports_without_mirage(module: str) -> None:
    code = _SUBPROCESS_TEMPLATE.format(module=module)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"importing {module!r} with mirage blocked failed:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert result.stdout.strip().endswith("OK")


def test_adapters_does_require_mirage() -> None:
    code = (
        "import sys\n"
        "class _B:\n"
        "    def find_spec(self, fullname, path=None, target=None):\n"
        "        if fullname == 'mirage' or fullname.startswith('mirage.'):\n"
        "            raise ModuleNotFoundError(fullname)\n"
        "        return None\n"
        "sys.meta_path.insert(0, _B())\n"
        "import importlib\n"
        "try:\n"
        "    importlib.import_module('mirage_dstest.adapters')\n"
        "except ModuleNotFoundError:\n"
        "    print('RAISED')\n"
        "else:\n"
        "    print('NO_RAISE')\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.stdout.strip() == "RAISED", (
        f"adapters should require mirage at import; got:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
