import { useSyncExternalStore } from "react";
import {
  getConsoleWorkspace,
  listConsoleWorkspaces,
} from "@/api/client";
import type {
  ConsoleWorkspaceBrief,
  ConsoleWorkspaceDetail,
} from "@/types/console";

const ACTIVE_KEY = "arcadia.console.active.v1";
const SESSIONS_KEY = "arcadia.console.sessions.v1";

interface ConsoleState {
  workspaces: ConsoleWorkspaceBrief[];
  details: Record<string, ConsoleWorkspaceDetail>;
  activeId: string | null;
  sessionByWorkspace: Record<string, string>;
  loaded: boolean;
  loading: boolean;
}

function readActive(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(ACTIVE_KEY);
  } catch {
    return null;
  }
}

function writeActive(id: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (id) window.localStorage.setItem(ACTIVE_KEY, id);
    else window.localStorage.removeItem(ACTIVE_KEY);
  } catch {
    /* ignore quota / private mode */
  }
}

function readSessions(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(SESSIONS_KEY);
    return raw ? (JSON.parse(raw) as Record<string, string>) : {};
  } catch {
    return {};
  }
}

function writeSessions(map: Record<string, string>) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(SESSIONS_KEY, JSON.stringify(map));
  } catch {
    /* ignore quota / private mode */
  }
}

let state: ConsoleState = {
  workspaces: [],
  details: {},
  activeId: readActive(),
  sessionByWorkspace: readSessions(),
  loaded: false,
  loading: false,
};

const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

function setState(patch: Partial<ConsoleState>) {
  state = { ...state, ...patch };
  emit();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getSnapshot(): ConsoleState {
  return state;
}

export function useConsoleStore(): ConsoleState {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export async function loadConsoleWorkspaces(): Promise<ConsoleWorkspaceBrief[]> {
  setState({ loading: true });
  try {
    const workspaces = await listConsoleWorkspaces();
    let activeId = state.activeId;
    if (activeId && !workspaces.some((w) => w.id === activeId)) {
      activeId = null;
      writeActive(null);
    }
    setState({ workspaces, activeId, loaded: true, loading: false });
    return workspaces;
  } catch (err) {
    setState({ loaded: true, loading: false });
    throw err;
  }
}

export async function refreshWorkspaceDetail(
  id: string,
): Promise<ConsoleWorkspaceDetail | null> {
  try {
    const detail = await getConsoleWorkspace(id);
    const workspaces = state.workspaces.map((w) =>
      w.id === id
        ? {
            ...w,
            mode: detail.mode,
            branch: detail.branch,
            status: detail.status,
            pending_effects: detail.pending_effects,
            mount_count: detail.mount_count,
          }
        : w,
    );
    const exists = workspaces.some((w) => w.id === id);
    setState({
      details: { ...state.details, [id]: detail },
      workspaces: exists ? workspaces : [detail, ...workspaces],
    });
    return detail;
  } catch {
    return null;
  }
}

export function setActiveWorkspace(id: string | null) {
  writeActive(id);
  setState({ activeId: id });
  if (id) void refreshWorkspaceDetail(id);
}

export function setWorkspaceSession(workspaceId: string, sessionId: string) {
  if (state.sessionByWorkspace[workspaceId] === sessionId) return;
  const sessionByWorkspace = {
    ...state.sessionByWorkspace,
    [workspaceId]: sessionId,
  };
  writeSessions(sessionByWorkspace);
  setState({ sessionByWorkspace });
}

export function selectWorkspaceSession(
  s: ConsoleState,
  workspaceId: string | null,
): string | null {
  return workspaceId ? s.sessionByWorkspace[workspaceId] ?? null : null;
}

export function upsertWorkspaceDetail(detail: ConsoleWorkspaceDetail) {
  const workspaces = state.workspaces.some((w) => w.id === detail.id)
    ? state.workspaces.map((w) => (w.id === detail.id ? { ...w, ...detail } : w))
    : [detail, ...state.workspaces];
  setState({
    details: { ...state.details, [detail.id]: detail },
    workspaces,
  });
}

export function selectActiveDetail(
  s: ConsoleState,
): ConsoleWorkspaceDetail | null {
  return s.activeId ? s.details[s.activeId] ?? null : null;
}

export function selectPendingCount(s: ConsoleState): number {
  if (!s.activeId) return 0;
  const detail = s.details[s.activeId];
  if (detail) return detail.pending_effects;
  const brief = s.workspaces.find((w) => w.id === s.activeId);
  return brief?.pending_effects ?? 0;
}
