import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../../test/mocks/server";
import {
  createConsoleWorkspace,
  promoteEffects,
  standupDryRun,
  testRunWorkspace,
} from "../client";

describe("console client", () => {
  it("createConsoleWorkspace posts name/template/mounts", async () => {
    server.use(
      http.post("/api/console/workspaces", async ({ request }) => {
        const body = (await request.json()) as {
          name: string;
          template_id: string;
          mounts: unknown[];
        };
        return HttpResponse.json({
          id: "w1",
          name: body.name,
          template_id: body.template_id,
          mode: "TEST",
          branch: "main",
          parent_id: null,
          status: "created",
          mount_count: body.mounts.length,
          pending_effects: 0,
          created_at: 0,
          mounts: [],
          snapshots: [],
          pinned_backing: false,
          error: null,
        });
      }),
    );
    const r = await createConsoleWorkspace({
      name: "x",
      template_id: "custom",
      mounts: [{ path: "/scratch", mode: "rw" }],
    });
    expect(r.id).toBe("w1");
    expect(r.mount_count).toBe(1);
  });

  it("standupDryRun returns projected mounts", async () => {
    server.use(
      http.post("/api/console/workspaces/:id/standup/dryrun", () =>
        HttpResponse.json({
          workspace_id: "w1",
          mounts: [
            { path: "/pagerduty", mode: "ro", effect_class: "external-effect", exists: true, bytes: 2048, files: 4 },
          ],
          estimated_snapshot_bytes: 2048,
          estimated_files: 4,
          cache_plan: "Pin backing snapshot of read-only mounts.",
        }),
      ),
    );
    const r = await standupDryRun("w1");
    expect(r.mounts[0].exists).toBe(true);
    expect(r.estimated_files).toBe(4);
  });

  it("testRunWorkspace dispatches the testing agent and returns a permission report", async () => {
    server.use(
      http.post("/api/console/workspaces/:id/test-run", () =>
        HttpResponse.json({
          workspace_id: "w1",
          ok: true,
          captured_writes: 1,
          steps: [
            { command: "ls -la /", exit_code: 0, stdout: "", op_count: 1, wrote: false, ok: true },
          ],
          permissions: [
            {
              prefix: "/pagerduty",
              mode: "read",
              effect_class: "external-effect",
              writable: false,
              expected_writable: false,
              enforced: true,
            },
            {
              prefix: "/scratch",
              mode: "write",
              effect_class: "scratch",
              writable: true,
              expected_writable: true,
              enforced: true,
            },
          ],
        }),
      ),
    );
    const r = await testRunWorkspace("w1");
    expect(r.ok).toBe(true);
    expect(r.captured_writes).toBe(1);
    expect(r.permissions.every((p) => p.enforced)).toBe(true);
  });

  it("promoteEffects posts the selected keys and reports simulated commit", async () => {
    server.use(
      http.post("/api/console/workspaces/:id/promote", async ({ request }) => {
        const body = (await request.json()) as { keys: string[] };
        return HttpResponse.json({
          results: body.keys.map((k) => ({ key: k, status: "promoted", simulated: true })),
          promoted_total: body.keys.length,
          pending: 0,
          simulated: true,
        });
      }),
    );
    const r = await promoteEffects("w1", ["0:write:/scratch/x"]);
    expect(r.simulated).toBe(true);
    expect(r.results[0].status).toBe("promoted");
    expect(r.pending).toBe(0);
  });
});
