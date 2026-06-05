import { useEffect } from "react";
import {
  NavLink,
  Outlet,
  Route,
  Routes,
  useNavigate,
} from "react-router-dom";
import {
  Activity,
  ArrowLeft,
  ChevronDown,
  FolderGit2,
  ListTree,
  Play,
  Send,
  Boxes,
} from "lucide-react";
import { useEventStream } from "@/hooks/useEventStream";
import { setWorkspaceMode } from "@/api/client";
import {
  loadConsoleWorkspaces,
  refreshWorkspaceDetail,
  selectActiveDetail,
  selectPendingCount,
  setActiveWorkspace,
  upsertWorkspaceDetail,
  useConsoleStore,
} from "@/lib/consoleStore";
import type { StreamEvent } from "@/types";
import { cn } from "@/lib/utils";
import { ModeBadge } from "@/components/console";
import WorkspacesPage from "./WorkspacesPage";
import RunPage from "./RunPage";
import StatePage from "./StatePage";
import TrajectoryPage from "./TrajectoryPage";
import PromotePage from "./PromotePage";

export interface ConsoleOutletCtx {
  events: StreamEvent[];
  connected: boolean;
}

const SUB_NAV = [
  { to: "/console", end: true, label: "Workspaces", icon: FolderGit2 },
  { to: "/console/run", end: false, label: "Run", icon: Play },
  { to: "/console/trajectory", end: false, label: "Trajectory", icon: ListTree },
  { to: "/console/state", end: false, label: "State", icon: Boxes },
  { to: "/console/promote", end: false, label: "Promote", icon: Send },
];

export default function ConsoleLayout() {
  const { events, connected } = useEventStream("/events");
  const store = useConsoleStore();
  const navigate = useNavigate();
  const active = selectActiveDetail(store);
  const pending = selectPendingCount(store);
  const isLive = active?.mode === "LIVE";

  useEffect(() => {
    loadConsoleWorkspaces().catch(() => {});
  }, []);

  useEffect(() => {
    if (store.activeId && !store.details[store.activeId]) {
      refreshWorkspaceDetail(store.activeId);
    }
  }, [store.activeId, store.details]);

  useEffect(() => {
    const last = events[events.length - 1] as unknown as
      | { type?: string; workspace_id?: string }
      | undefined;
    if (!last || !store.activeId) return;
    const t = last.type ?? "";
    if (
      t.startsWith("console_") &&
      (last.workspace_id === store.activeId || t === "console_promote")
    ) {
      refreshWorkspaceDetail(store.activeId);
    }
  }, [events, store.activeId]);

  async function toggleMode() {
    if (!active) return;
    const next = active.mode === "TEST" ? "LIVE" : "TEST";
    if (
      next === "LIVE" &&
      !window.confirm(
        "Switch this workspace to LIVE?\n\nIn LIVE mode, writes to durable / " +
          "system-of-record mounts pass through to real backends. External " +
          "effects still route through Promote. This is deliberate and logged.",
      )
    ) {
      return;
    }
    const detail = await setWorkspaceMode(active.id, next);
    upsertWorkspaceDetail(detail);
  }

  return (
    <div
      className={cn(
        "flex h-screen min-w-[980px] flex-col overflow-hidden text-text-primary",
        isLive && "chrome-live",
      )}
    >
      <header
        className={cn(
          "flex h-12 shrink-0 items-center gap-3 border-b border-border bg-surface-1/80 px-3 backdrop-blur-xl",
          isLive && "chrome-live-bar",
        )}
      >
        <button
          onClick={() => navigate("/")}
          title="Back to Operations"
          className="flex h-7 items-center gap-1.5 rounded-md px-2 text-[12px] text-text-muted transition-colors hover:bg-surface-3 hover:text-text-primary"
        >
          <ArrowLeft size={14} />
        </button>
        <div className="flex items-center gap-2">
          <div className="grid h-7 w-7 place-items-center rounded-lg bg-gradient-to-br from-accent to-info text-white">
            <Boxes size={15} />
          </div>
          <span className="text-[13px] font-semibold tracking-tight">
            Mirage Console
          </span>
        </div>

        <div className="mx-1 h-5 w-px bg-border" />

        <WorkspaceSwitcher />

        {active && (
          <>
            <span className="font-mono text-[11px] text-text-faint">·</span>
            <span
              className="font-mono text-[11px] text-text-muted"
              title="Active branch"
            >
              {active.branch}
            </span>
            <ModeBadge
              mode={active.mode}
              size="sm"
              onClick={toggleMode}
              className="ml-1"
            />
          </>
        )}

        <div className="ml-auto flex items-center gap-2.5">
          <button
            onClick={() => navigate("/console/promote")}
            className={cn(
              "flex h-7 items-center gap-1.5 rounded-md border px-2.5 text-[11px] font-medium transition-colors",
              pending > 0
                ? "border-simulated/40 bg-simulated-soft text-simulated hover:border-simulated/60"
                : "border-border bg-surface-2 text-text-muted hover:text-text-secondary",
            )}
            title="Captured effects pending promotion"
          >
            <span>captured effects pending</span>
            <span
              key={pending}
              className={cn(
                "rounded px-1 font-mono tabular-nums",
                pending > 0 && "animate-capture-flash",
              )}
            >
              {pending}
            </span>
          </button>
          <span className="flex items-center gap-1.5 text-[11px] text-text-muted">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                connected ? "bg-success" : "bg-danger",
              )}
            />
            <Activity size={13} className="text-text-faint" />
          </span>
        </div>
      </header>

      <nav className="flex h-10 shrink-0 items-center gap-1 border-b border-border bg-surface-0 px-3">
        {SUB_NAV.map((item) => {
          const disabled = !active && item.to !== "/console";
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={(e) => {
                if (disabled) e.preventDefault();
              }}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[12px] font-medium transition-colors",
                  disabled && "cursor-not-allowed opacity-40",
                  isActive && !disabled
                    ? "bg-accent-soft text-accent"
                    : "text-text-secondary hover:bg-surface-2 hover:text-text-primary",
                )
              }
            >
              <item.icon size={14} />
              {item.label}
            </NavLink>
          );
        })}
        {isLive && (
          <span className="ml-auto flex items-center gap-1.5 rounded-md border border-live/50 bg-live-soft px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-live">
            LIVE mode — real writes enabled
          </span>
        )}
      </nav>

      <main className="relative min-h-0 flex-1 overflow-hidden">
        <Routes>
          <Route element={<ConsoleOutlet events={events} connected={connected} />}>
            <Route index element={<WorkspacesPage />} />
            <Route path="run" element={<RunPage />} />
            <Route path="trajectory" element={<TrajectoryPage />} />
            <Route path="state" element={<StatePage />} />
            <Route path="promote" element={<PromotePage />} />
          </Route>
        </Routes>
      </main>
    </div>
  );
}

function ConsoleOutlet({ events, connected }: ConsoleOutletCtx) {
  return <Outlet context={{ events, connected } satisfies ConsoleOutletCtx} />;
}

function WorkspaceSwitcher() {
  const store = useConsoleStore();
  const active = selectActiveDetail(store);
  return (
    <div className="relative">
      <select
        value={store.activeId ?? ""}
        onChange={(e) => setActiveWorkspace(e.target.value || null)}
        className="h-7 max-w-[220px] rounded-md border border-border bg-surface-2 pl-2.5 pr-7 text-[12px] text-text-primary outline-none"
      >
        <option value="">— no workspace —</option>
        {store.workspaces.map((w) => (
          <option key={w.id} value={w.id}>
            {w.name}
          </option>
        ))}
      </select>
      {!active && (
        <ChevronDown
          size={13}
          className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-text-muted"
        />
      )}
    </div>
  );
}
