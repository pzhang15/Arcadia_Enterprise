import { describe, expect, it } from "vitest";
import {
  selectActiveDetail,
  selectPendingCount,
  selectWorkspaceSession,
  setWorkspaceSession,
} from "../consoleStore";
import type {
  ConsoleWorkspaceBrief,
  ConsoleWorkspaceDetail,
} from "@/types/console";

type State = Parameters<typeof selectPendingCount>[0];

function brief(over: Partial<ConsoleWorkspaceBrief> = {}): ConsoleWorkspaceBrief {
  return {
    id: "w1",
    name: "ws",
    template_id: "custom",
    mode: "TEST",
    branch: "main",
    parent_id: null,
    status: "ready",
    mount_count: 1,
    pending_effects: 0,
    created_at: 0,
    ...over,
  };
}

function detail(over: Partial<ConsoleWorkspaceDetail> = {}): ConsoleWorkspaceDetail {
  return {
    ...brief(),
    mounts: [],
    snapshots: [],
    pinned_backing: true,
    error: null,
    ...over,
  };
}

function state(over: Partial<State> = {}): State {
  return {
    workspaces: [],
    details: {},
    activeId: null,
    sessionByWorkspace: {},
    loaded: true,
    loading: false,
    ...over,
  } as State;
}

describe("consoleStore selectors", () => {
  it("returns null/0 when there is no active workspace", () => {
    const s = state();
    expect(selectActiveDetail(s)).toBeNull();
    expect(selectPendingCount(s)).toBe(0);
  });

  it("prefers the loaded detail's pending count", () => {
    const s = state({
      activeId: "w1",
      details: { w1: detail({ id: "w1", pending_effects: 3 }) },
      workspaces: [brief({ id: "w1", pending_effects: 99 })],
    });
    expect(selectActiveDetail(s)?.id).toBe("w1");
    expect(selectPendingCount(s)).toBe(3);
  });

  it("falls back to the brief's pending count when no detail is loaded", () => {
    const s = state({
      activeId: "w1",
      details: {},
      workspaces: [brief({ id: "w1", pending_effects: 7 })],
    });
    expect(selectActiveDetail(s)).toBeNull();
    expect(selectPendingCount(s)).toBe(7);
  });
});

describe("consoleStore workspace -> session mapping", () => {
  it("selectWorkspaceSession reads the remembered session for a workspace", () => {
    const s = state({ sessionByWorkspace: { w1: "s1" } });
    expect(selectWorkspaceSession(s, "w1")).toBe("s1");
    expect(selectWorkspaceSession(s, "w2")).toBeNull();
    expect(selectWorkspaceSession(s, null)).toBeNull();
  });

  it("setWorkspaceSession persists the mapping so a switch-back reattaches", () => {
    const key = "arcadia.console.sessions.v1";
    setWorkspaceSession("ws-persist", "sess-xyz");
    const map = JSON.parse(window.localStorage.getItem(key) as string);
    expect(map["ws-persist"]).toBe("sess-xyz");
    // Remembering another workspace keeps the prior mapping intact.
    setWorkspaceSession("ws-other", "sess-2");
    const map2 = JSON.parse(window.localStorage.getItem(key) as string);
    expect(map2["ws-persist"]).toBe("sess-xyz");
    expect(map2["ws-other"]).toBe("sess-2");
  });
});
