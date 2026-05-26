import { useState } from "react";
import { Routes, Route, NavLink, useLocation } from "react-router-dom";
import { useEventStream } from "./hooks/useEventStream";
import AgentWorkspace from "./pages/AgentWorkspace";
import VFSExplorer from "./pages/VFSExplorer";
import DataBrowser from "./pages/DataBrowser";
import TracesView from "./pages/TracesView";
import ScorecardView from "./pages/ScorecardView";

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  section: string;
}

const NAV_ITEMS: NavItem[] = [
  {
    path: "/",
    label: "Agent Workspace",
    icon: <AgentIcon />,
    section: "Agent",
  },
  {
    path: "/vfs",
    label: "VFS Explorer",
    icon: <FolderIcon />,
    section: "Agent",
  },
  {
    path: "/data",
    label: "Data Browser",
    icon: <DatabaseIcon />,
    section: "Data",
  },
  {
    path: "/traces",
    label: "Trace Timeline",
    icon: <TimelineIcon />,
    section: "Observability",
  },
  {
    path: "/scorecard",
    label: "Scorecard",
    icon: <ChartIcon />,
    section: "Observability",
  },
];

export default function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const { events, connected } = useEventStream("/events");
  const location = useLocation();

  let currentSection = "";

  return (
    <div className="flex h-full w-full">
      <nav
        className={`flex flex-col border-r border-border bg-surface-1 transition-all duration-200 ${sidebarCollapsed ? "w-[60px]" : "w-[240px]"}`}
      >
        <div className="flex items-center gap-2 border-b border-border px-4 py-4">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent text-xs font-bold text-white">
            A
          </div>
          {!sidebarCollapsed && (
            <div className="flex flex-col overflow-hidden">
              <span className="truncate text-sm font-semibold text-text-primary">
                Arcadia
              </span>
              <span className="truncate text-[10px] text-text-muted">
                platform
              </span>
            </div>
          )}
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="ml-auto flex h-6 w-6 shrink-0 items-center justify-center rounded text-text-muted transition-colors hover:bg-surface-3 hover:text-text-primary"
          >
            <svg
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className={`h-3.5 w-3.5 transition-transform ${sidebarCollapsed ? "rotate-180" : ""}`}
            >
              <path d="M10 3L5 8l5 5" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-2">
          {NAV_ITEMS.map((item) => {
            const showSection = item.section !== currentSection;
            if (showSection) currentSection = item.section;
            const isActive =
              item.path === "/"
                ? location.pathname === "/"
                : location.pathname.startsWith(item.path);

            return (
              <div key={item.path}>
                {showSection && !sidebarCollapsed && (
                  <div className="px-3 pb-1 pt-4 text-[10px] font-semibold uppercase tracking-widest text-text-muted">
                    {item.section}
                  </div>
                )}
                <NavLink
                  to={item.path}
                  end={item.path === "/"}
                  className={`mx-2 flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-[13px] transition-colors ${
                    isActive
                      ? "bg-accent-muted text-accent"
                      : "text-text-secondary hover:bg-surface-3 hover:text-text-primary"
                  } ${sidebarCollapsed ? "justify-center" : ""}`}
                  title={sidebarCollapsed ? item.label : undefined}
                >
                  <span className="flex h-4 w-4 shrink-0 items-center justify-center [&>svg]:h-4 [&>svg]:w-4">
                    {item.icon}
                  </span>
                  {!sidebarCollapsed && (
                    <span className="truncate">{item.label}</span>
                  )}
                </NavLink>
              </div>
            );
          })}
        </div>

        <div className="border-t border-border px-3 py-3">
          <div className="flex items-center gap-2">
            <div
              className={`h-1.5 w-1.5 shrink-0 rounded-full ${connected ? "bg-success" : "bg-danger"}`}
            />
            {!sidebarCollapsed && (
              <span className="text-xs text-text-muted">
                {connected ? "Connected" : "Disconnected"}
              </span>
            )}
            {!sidebarCollapsed && events.length > 0 && (
              <span className="ml-auto font-mono text-[10px] text-text-muted">
                {events.length}
              </span>
            )}
          </div>
        </div>
      </nav>

      <main className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<AgentWorkspace events={events} />} />
          <Route path="/vfs" element={<VFSExplorer />} />
          <Route path="/data" element={<DataBrowser />} />
          <Route path="/traces" element={<TracesView events={events} />} />
          <Route path="/scorecard" element={<ScorecardView />} />
        </Routes>
      </main>
    </div>
  );
}

function AgentIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="2" width="12" height="12" rx="2" />
      <path d="M5 6l2.5 2.5L5 11M9 11h3" />
    </svg>
  );
}

function FolderIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M2 4.5A1.5 1.5 0 013.5 3H6l1.5 1.5h5A1.5 1.5 0 0114 6v5.5a1.5 1.5 0 01-1.5 1.5h-9A1.5 1.5 0 012 11.5z" />
    </svg>
  );
}

function DatabaseIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <ellipse cx="8" cy="4" rx="5" ry="2" />
      <path d="M3 4v8c0 1.1 2.2 2 5 2s5-.9 5-2V4" />
      <path d="M3 8c0 1.1 2.2 2 5 2s5-.9 5-2" />
    </svg>
  );
}

function TimelineIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M2 3h12M2 8h8M2 13h10" />
    </svg>
  );
}

function ChartIcon() {
  return (
    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M4 14V8M8 14V4M12 14V6" />
    </svg>
  );
}
