import { describe, expect, it } from "vitest";
import type { ReplayAction } from "@/types/replay";
import {
  foldReplay,
  groupActionsByToolCall,
  intentEffectFlag,
} from "../replayFold";

function act(over: Partial<ReplayAction>): ReplayAction {
  return {
    idx: 0,
    op: "read",
    path: "/s3/a.json",
    source: "s3",
    bytes: 100,
    duration_ms: 5,
    mount_prefix: "/s3",
    fingerprint: null,
    revision: null,
    is_cache: false,
    tool_call_id: "tc1",
    run_id: "r1",
    timestamp: 0,
    ...over,
  };
}

describe("foldReplay", () => {
  const actions = [
    act({ idx: 0, op: "read", path: "/s3/a.json" }),
    act({ idx: 1, op: "read", path: "/s3/b.json" }),
    act({ idx: 2, op: "write", path: "/rca.md", bytes: 4280, source: "ram" }),
  ];

  it("grows reads-so-far and excludes the future", () => {
    expect(foldReplay(actions, 0).reads_so_far).toEqual(["/s3/a.json"]);
    expect(foldReplay(actions, 1).reads_so_far).toEqual([
      "/s3/a.json",
      "/s3/b.json",
    ]);
    expect(foldReplay(actions, 1).overlay).toEqual([]);
  });

  it("applies a write to the overlay and surfaces a write diff at the cursor", () => {
    const s = foldReplay(actions, 2);
    expect(s.overlay.map((o) => o.path)).toEqual(["/rca.md"]);
    expect(s.diff?.kind).toBe("write");
    expect(s.diff?.added_bytes).toBe(4280);
  });

  it("surfaces a read diff with cache + fingerprint at the cursor", () => {
    const a = [act({ idx: 0, is_cache: true, fingerprint: "etag-9a1f" })];
    const d = foldReplay(a, 0).diff;
    expect(d?.kind).toBe("read");
    expect(d?.is_cache).toBe(true);
    expect(d?.fingerprint).toBe("etag-9a1f");
  });

  it("returns an empty state before the start (cursor -1)", () => {
    const s = foldReplay(actions, -1);
    expect(s.cursor_op).toBeNull();
    expect(s.reads_so_far).toEqual([]);
  });
});

describe("groupActionsByToolCall", () => {
  it("groups by tool_call_id, bucketing unlinked ops", () => {
    const m = groupActionsByToolCall([
      act({ idx: 0, tool_call_id: "tcA" }),
      act({ idx: 1, tool_call_id: "tcA" }),
      act({ idx: 2, tool_call_id: null }),
    ]);
    expect(m.get("tcA")?.length).toBe(2);
    expect(m.get("__unlinked__")?.length).toBe(1);
  });
});

describe("intentEffectFlag", () => {
  it("fires when a 'live' intent meets a cached read", () => {
    const f = intentEffectFlag("read the live dashboard", act({ is_cache: true }));
    expect(f.mismatch).toBe(true);
  });

  it("fires when a 'live' intent meets a stale-looking path", () => {
    const f = intentEffectFlag(
      "fetch the current numbers",
      act({ path: "/s3/dashboards/checkout_2023.json" }),
    );
    expect(f.mismatch).toBe(true);
  });

  it("never fires without intent, or without a freshness claim", () => {
    expect(intentEffectFlag(undefined, act({ is_cache: true })).mismatch).toBe(
      false,
    );
    expect(
      intentEffectFlag("read the file", act({ is_cache: true })).mismatch,
    ).toBe(false);
  });
});
