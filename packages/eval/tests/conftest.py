import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_EVAL_ROOT = _REPO_ROOT / "packages" / "eval"
_STORE_ROOT = _REPO_ROOT / "packages" / "store"
_MIRAGE_PYTHON = _REPO_ROOT / "vendor" / "mirage" / "python"
for _p in (_MIRAGE_PYTHON, _EVAL_ROOT, _STORE_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
