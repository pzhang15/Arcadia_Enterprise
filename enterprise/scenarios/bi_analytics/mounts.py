"""Mounts for the bi_analytics scenario. TODO: implement."""
from pathlib import Path

from mirage import MountMode, RAMResource, Workspace

DEFAULT_DISK_ROOT = (Path(__file__).resolve().parent / 'fixture'
                     / 'disk').resolve()

def build_l1_workspace(disk_root=None, *, agent_id='mirage-eval',
                       session_id='default'):
    return Workspace(
        {'/': (RAMResource(), MountMode.WRITE)},
        mode=MountMode.WRITE,
        agent_id=agent_id,
        session_id=session_id)
