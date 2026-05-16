from pathlib import Path

from mirage import Workspace


def snapshot_workspace(ws: Workspace, snapshot_path: str | Path) -> Path:
    """Write the workspace state to a tar at ``snapshot_path``.

    Args:
        ws (Workspace): A constructed (and optionally pre-warmed) workspace.
        snapshot_path (str | Path): Destination tar file path. Parent dirs
            are created if missing.
    """
    target = Path(snapshot_path).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    ws.snapshot(str(target))
    return target
