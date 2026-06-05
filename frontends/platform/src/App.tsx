import { useEffect, useState } from "react";
import { Routes, Route, NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  BarChart3,
  Boxes,
  ChevronsLeft,
  ClipboardList,
  Database,
  FolderTree,
  HelpCircle,
  Send,
  Settings,
} from "lucide-react";
import { useEventStream } from "./hooks/useEventStream";
import { getConfig } from "./api/client";
import { hydrateInvestigations } from "./lib/investigationStore";
import InboxPage from "./pages/InboxPage";
import DispatchPage from "./pages/DispatchPage";
import InvestigationDetail from "./pages/InvestigationDetail";
import VFSExplorer from "./pages/VFSExplorer";
import DataBrowser from "./pages/DataBrowser";
import TracesView from "./pages/TracesView";
import ScorecardView from "./pages/ScorecardView";
import ConsoleLayout from "./console/ConsoleLayout";
import ConsoleV3 from "./console/v3/ConsoleV3";
import { cn } from "./lib/utils";

interface NavItem {
  path: string;
  match?: (pathname: string) => boolean;
  label: string;
  icon: React.ReactNode;
  section: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    path: "/",
    match: (p) => p === "/" || p.startsWith("/investigations"),
    label: "Inbox",
    icon: <ClipboardList size={16} strokeWidth={1.75} />,
    section: "Operations",
  },
  {
    path: "/dispatch",
    label: "Dispatch",
    icon: <Send size={16} strokeWidth={1.75} />,
    section: "Operations",
  },
  {
    path: "/vfs",
    label: "Workspace Inspector",
    icon: <FolderTree size={16} strokeWidth={1.75} />,
    section: "Investigate",
  },
  {
    path: "/data",
    label: "Data Catalog",
    icon: <Database size={16} strokeWidth={1.75} />,
    section: "Investigate",
  },
  {
    path: "/observability",
    label: "Observability",
    icon: <Activity size={16} strokeWidth={1.75} />,
    section: "Govern",
  },
  {
    path: "/evaluations",
    label: "Evaluations",
    icon: <BarChart3 size={16} strokeWidth={1.75} />,
    section: "Govern",
  },
  {
    path: "/console",
    match: (p) => p.startsWith("/console"),
    label: "Mirage Console",
    icon: <Boxes size={16} strokeWidth={1.75} />,
    section: "Develop",
  },
];

export default function App() {
  const location = useLocation();
  if (location.pathname.startsWith("/v3")) {
    return (
      <Routes>
        <Route path="/v3/*" element={<ConsoleV3 />} />
      </Routes>
    );
  }
  if (location.pathname.startsWith("/console")) {
    return (
      <Routes>
        <Route path="/console/*" element={<ConsoleLayout />} />
      </Routes>
    );
  }
  return <OpsShell />;
}

function OpsShell() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { events, connected } = useEventStream("/events");
  const location = useLocation();
  const [model, setModel] = useState<string>("");
  const [baseUrl, setBaseUrl] = useState<string>("");

  useEffect(() => {
    getConfig()
      .then((c) => {
        setModel(c.model);
        if (
          c &&
          typeof (c as unknown as { base_url?: string }).base_url === "string"
        ) {
          setBaseUrl((c as unknown as { base_url: string }).base_url);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    hydrateInvestigations();
  }, []);

  let currentSection = "";

  return (
    <div className="flex h-screen min-w-[980px] overflow-hidden text-text-primary">
      <nav
        className={cn(
          "relative z-10 flex shrink-0 flex-col border-r border-border bg-surface-1/80 backdrop-blur-xl transition-[width] duration-200",
          sidebarCollapsed ? "w-[64px]" : "w-[244px]",
        )}
      >
        <div
          className={cn(
            "flex h-14 shrink-0 items-center gap-3 border-b border-border px-3",
            sidebarCollapsed && "justify-center px-2",
          )}
        >
          <div className="relative shrink-0">
            <div className="absolute -inset-1 rounded-xl bg-gradient-to-br from-accent/60 to-info/40 opacity-50 blur-md" />
            <div className="relative grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-accent to-info text-white shadow-sm">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.25"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M3 21l9-18 9 18" />
                <path d="M7.5 14h9" />
              </svg>
            </div>
          </div>
          {!sidebarCollapsed && (
            <div className="flex min-w-0 flex-col leading-tight">
              <span className="truncate text-[14px] font-semibold tracking-tight text-text-primary">
                Arcadia
              </span>
              <span className="truncate text-[11px] text-text-muted">
                Operations · Production
              </span>
            </div>
          )}
          {!sidebarCollapsed && (
            <button
              onClick={() => setSidebarCollapsed(true)}
              className="ml-auto grid h-7 w-7 shrink-0 place-items-center rounded-md text-text-muted transition-colors hover:bg-surface-3 hover:text-text-primary"
              title="Collapse sidebar"
            >
              <ChevronsLeft size={15} />
            </button>
          )}
        </div>

        {sidebarCollapsed && (
          <button
            onClick={() => setSidebarCollapsed(false)}
            className="mx-auto mt-2 grid h-7 w-7 place-items-center rounded-md text-text-muted transition-colors hover:bg-surface-3 hover:text-text-primary"
            title="Expand sidebar"
          >
            <ChevronsLeft size={15} className="rotate-180" />
          </button>
        )}

        <div className="flex-1 overflow-y-auto px-2 py-3">
          {NAV_ITEMS.map((item) => {
            const showSection = item.section !== currentSection;
            if (showSection) currentSection = item.section;
            const isActive = item.match
              ? item.match(location.pathname)
              : location.pathname === item.path;

            return (
              <div key={item.path}>
                {showSection && !sidebarCollapsed && (
                  <div className="px-2 pb-1.5 pt-4 text-[10px] font-semibold uppercase tracking-[0.1em] text-text-faint first:pt-0">
                    {item.section}
                  </div>
                )}
                <NavLink
                  to={item.path}
                  end={item.path === "/"}
                  title={sidebarCollapsed ? item.label : undefined}
                  className={cn(
                    "group relative my-0.5 flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] transition-all duration-150 ease-out",
                    isActive
                      ? "bg-accent-soft text-accent"
                      : "text-text-secondary hover:bg-surface-3 hover:text-text-primary",
                    sidebarCollapsed && "justify-center px-0",
                  )}
                >
                  {isActive && (
                    <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-x-2 -translate-y-1/2 rounded-full bg-accent" />
                  )}
                  <span
                    className={cn(
                      "flex h-4 w-4 shrink-0 items-center justify-center",
                      isActive ? "text-accent" : "text-text-muted group-hover:text-text-secondary",
                    )}
                  >
                    {item.icon}
                  </span>
                  {!sidebarCollapsed && (
                    <span className="min-w-0 flex-1 truncate font-medium">
                      {item.label}
                    </span>
                  )}
                </NavLink>
              </div>
            );
          })}
        </div>

        <div className="border-t border-border p-2.5">
          {!sidebarCollapsed ? (
            <>
              <div className="mb-2 flex items-center justify-between gap-2 rounded-lg bg-surface-2 px-2.5 py-2">
                <div className="flex min-w-0 items-center gap-2">
                  <div className="relative shrink-0">
                    <span
                      className={cn(
                        "block h-2 w-2 rounded-full",
                        connected ? "bg-success" : "bg-danger",
                      )}
                    />
                    {connected && (
                      <span className="absolute inset-0 animate-ping rounded-full bg-success opacity-60" />
                    )}
                  </div>
                  <div className="min-w-0 leading-tight">
                    <div className="truncate text-[11px] font-medium text-text-secondary">
                      {connected ? "Connected" : "Offline"}
                    </div>
                    <div className="truncate text-[10px] text-text-muted">
                      {events.length} events
                    </div>
                  </div>
                </div>
                {model && (
                  <span
                    className="rounded-md border border-border bg-surface-1 px-1.5 py-0.5 font-mono text-[10px] text-text-muted"
                    title={baseUrl ? `Routed via ${baseUrl}` : undefined}
                  >
                    {model}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                <button className="grid h-8 flex-1 place-items-center rounded-lg text-text-muted transition-colors hover:bg-surface-3 hover:text-text-primary">
                  <Settings size={14} />
                </button>
                <button className="grid h-8 flex-1 place-items-center rounded-lg text-text-muted transition-colors hover:bg-surface-3 hover:text-text-primary">
                  <HelpCircle size={14} />
                </button>
              </div>
            </>
          ) : (
            <div className="flex flex-col items-center gap-2">
              <span
                className={cn(
                  "block h-2 w-2 rounded-full",
                  connected ? "bg-success" : "bg-danger",
                )}
              />
              <button className="grid h-7 w-7 place-items-center rounded-md text-text-muted transition-colors hover:bg-surface-3 hover:text-text-primary">
                <Settings size={14} />
              </button>
            </div>
          )}
        </div>
      </nav>

      <main className="relative min-w-0 flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<InboxPage />} />
          <Route path="/dispatch" element={<DispatchPage />} />
          <Route
            path="/investigations/:sessionId"
            element={<InvestigationDetail events={events} />}
          />
          <Route path="/vfs" element={<VFSExplorer />} />
          <Route path="/data" element={<DataBrowser />} />
          <Route path="/observability" element={<TracesView events={events} />} />
          <Route path="/evaluations" element={<ScorecardView />} />
          {/* Legacy redirects */}
          <Route path="/traces" element={<TracesView events={events} />} />
          <Route path="/scorecard" element={<ScorecardView />} />
        </Routes>
      </main>
    </div>
  );
}
