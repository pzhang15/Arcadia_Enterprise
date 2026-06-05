import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../../test/mocks/server";
import { getReplay } from "../client";

const WRITE_OP = {
  idx: 1,
  op: "write",
  path: "/rca.md",
  source: "ram",
  bytes: 4280,
  duration_ms: 6,
  mount_prefix: "/",
  fingerprint: null,
  revision: null,
  is_cache: true,
  tool_call_id: "tc1",
  run_id: "r1",
  timestamp: 20,
};

describe("getReplay", () => {
  it("requests the session replay and parses actions + folded state", async () => {
    server.use(
      http.get("/api/sessions/sess1/replay", ({ request }) => {
        const url = new URL(request.url);
        expect(url.searchParams.get("cursor")).toBe("1");
        return HttpResponse.json({
          session_id: "sess1",
          run_id: "r1",
          cursor: 1,
          total: 2,
          actions: [
            {
              idx: 0,
              op: "read",
              path: "/s3/a.json",
              source: "s3",
              bytes: 100,
              duration_ms: 5,
              mount_prefix: "/s3",
              fingerprint: "etag-9a1f",
              revision: "v3",
              is_cache: false,
              tool_call_id: "tc1",
              run_id: "r1",
              timestamp: 10,
            },
            WRITE_OP,
          ],
          state: {
            overlay: [
              { path: "/rca.md", op: "write", bytes: 4280, mount_prefix: "/" },
            ],
            reads_so_far: ["/s3/a.json"],
            reads_count: 1,
            cursor_op: WRITE_OP,
            diff: {
              kind: "write",
              path: "/rca.md",
              added_bytes: 4280,
              mount_prefix: "/",
            },
          },
        });
      }),
    );

    const r = await getReplay("sess1", 1);
    expect(r.total).toBe(2);
    // Phase-0 correlation + dropped fields are now present on the action.
    expect(r.actions[0].tool_call_id).toBe("tc1");
    expect(r.actions[0].fingerprint).toBe("etag-9a1f");
    expect(r.actions[0].revision).toBe("v3");
    // stateAt(cursor) fold.
    expect(r.state.reads_so_far).toEqual(["/s3/a.json"]);
    expect(r.state.overlay.map((o) => o.path)).toEqual(["/rca.md"]);
    expect(r.state.diff?.kind).toBe("write");
    expect(r.state.diff?.added_bytes).toBe(4280);
  });
});
