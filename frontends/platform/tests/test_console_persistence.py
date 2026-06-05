import server

from arcadia_store import StoreConfig, build_store, run_migrations


async def test_console_workspace_survives_restart(tmp_path):
    dsn = f"sqlite+aiosqlite:///{tmp_path}/console.db"
    await run_migrations(dsn)
    store = build_store(StoreConfig(dsn=dsn))
    await store.init()
    original = server._store
    server._store = store
    try:
        server._console_workspaces.clear()
        cws = server.ConsoleWorkspace(
            id="ws-restart",
            name="demo",
            template_id="custom",
            mounts=[server.ConsoleMount(prefix="/scratch", resource="ram",
                                        mode="rw", effect_class="scratch")],
            mount_specs=[{"path": "/scratch", "mode": "rw"}],
            status="ready",
            created_at=1.0,
            promoted_keys={"0:write:/scratch/a"},
            snapshots=[{"name": "snap-1", "path": "/tmp/x.tar", "size": 10,
                        "created_at": 1.0}],
        )
        cws._effects_cache = [{"key": "0:write:/scratch/a", "op": "write",
                               "path": "/scratch/a", "promoted": True}]
        await server._persist_console(cws)

        # Simulate restart: in-memory workspaces gone, rehydrate from store.
        server._console_workspaces.clear()
        await server._rehydrate_console_workspaces()

        restored = server._console_workspaces.get("ws-restart")
        assert restored is not None
        assert restored.workspace is None
        assert restored.promoted_keys == {"0:write:/scratch/a"}
        assert restored.snapshots[0]["name"] == "snap-1"
        # cached effects survive even though the live workspace does not
        assert server._console_effects(restored)[0]["key"] == "0:write:/scratch/a"
        detail = server._console_detail(restored)
        assert detail["status"] == "ready"
        assert detail["mount_count"] == 1

        await store.delete_console_workspace("ws-restart")
    finally:
        server._store = original
        server._console_workspaces.pop("ws-restart", None)
        await store.close()
