"""Seed for the bi_analytics scenario. TODO: implement."""
from pathlib import Path

DEFAULT_ROOT = str(
    (Path(__file__).resolve().parent / 'fixture' / 'disk').resolve())

def main(root=DEFAULT_ROOT, *, clean=True):
    target = Path(root).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target
