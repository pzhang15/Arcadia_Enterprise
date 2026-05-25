import argparse
from pathlib import Path

from mirage_eval.fixtures.build_snapshot import snapshot_workspace
from scenarios.onboarding_it import seed
from scenarios.onboarding_it.mounts import (DEFAULT_DISK_ROOT,
                                            build_l1_workspace)

DEFAULT_SNAPSHOT = (Path(__file__).resolve().parent / "corpus.tar")


def build(disk_root: str | Path | None = None,
          snapshot_path: str | Path | None = None) -> Path:
    """Seed the disk corpus and snapshot the workspace to a tar.

    Args:
        disk_root (str | Path | None): Disk root for the seed; default
            ``~/mirage-eval/onboarding_it``.
        snapshot_path (str | Path | None): Output tar path; default
            ``scenarios/onboarding_it/fixture/corpus.tar``.
    """
    root = Path(disk_root or DEFAULT_DISK_ROOT).expanduser().resolve()
    seed.main(root, clean=True)
    target = Path(snapshot_path or DEFAULT_SNAPSHOT).expanduser().resolve()
    ws = build_l1_workspace(disk_root=root, session_id="fixture-build")
    return snapshot_workspace(ws, target)


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Seed corpus and snapshot the L1 workspace to a tar.")
    parser.add_argument("--disk-root", default=None)
    parser.add_argument("--snapshot-path", default=None)
    args = parser.parse_args()
    out = build(args.disk_root, args.snapshot_path)
    print(f"snapshot written: {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    _cli()
