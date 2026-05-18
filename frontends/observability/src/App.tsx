import { useState } from "react";
import { useEventStream } from "./hooks/useEventStream";
import CommandTimeline from "./components/CommandTimeline";
import MockRequestLog from "./components/MockRequestLog";
import ScoreCardDashboard from "./components/ScoreCardDashboard";
import ResourceMap from "./components/ResourceMap";
import McpTraffic from "./components/McpTraffic";

type View = "timeline" | "requests" | "scorecard" | "resources" | "mcp";

const NAV: { id: View; label: string; icon: string; section: string }[] = [
  { id: "timeline", label: "Command Timeline", icon: "timeline", section: "Live" },
  { id: "mcp", label: "MCP Traffic", icon: "mcp", section: "Live" },
  { id: "requests", label: "Request Log", icon: "requests", section: "Live" },
  { id: "resources", label: "Resource Map", icon: "resources", section: "Live" },
  { id: "scorecard", label: "Scorecard", icon: "scorecard", section: "Results" },
];

function NavIcon({ icon }: { icon: string }) {
  switch (icon) {
    case "timeline":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M2 3h12M2 8h8M2 13h10" />
        </svg>
      );
    case "requests":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="2" y="2" width="12" height="12" rx="2" />
          <path d="M2 6h12M6 6v8" />
        </svg>
      );
    case "scorecard":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M4 14V8M8 14V4M12 14V6" />
        </svg>
      );
    case "resources":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="4" cy="4" r="2" />
          <circle cx="12" cy="4" r="2" />
          <circle cx="8" cy="12" r="2" />
          <path d="M5.5 5.5L7 10.5M10.5 5.5L9 10.5" />
        </svg>
      );
    case "mcp":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M3 4l3 4-3 4M9 12h4" />
        </svg>
      );
    default:
      return null;
  }
}

export default function App() {
  const [view, setView] = useState<View>("timeline");
  const { events, connected, clear } = useEventStream("/events");

  let currentSection = "";

  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-logo">
          Mirage <span>observability</span>
        </div>
        {NAV.map((item) => {
          const showSection = item.section !== currentSection;
          if (showSection) currentSection = item.section;
          return (
            <div key={item.id}>
              {showSection && (
                <div className="sidebar-section">{item.section}</div>
              )}
              <div
                className={`sidebar-item ${view === item.id ? "active" : ""}`}
                onClick={() => setView(item.id)}
              >
                <NavIcon icon={item.icon} />
                {item.label}
              </div>
            </div>
          );
        })}
        <div className="sidebar-footer">
          <div className="connection-status">
            <div className={`connection-dot ${connected ? "connected" : ""}`} />
            {connected ? "Connected" : "Disconnected"}
            {events.length > 0 && (
              <span className="text-tertiary" style={{ marginLeft: "auto" }}>
                {events.length}
              </span>
            )}
          </div>
        </div>
      </nav>
      <main className="main-content">
        {view === "timeline" && (
          <CommandTimeline events={events} onClear={clear} />
        )}
        {view === "requests" && <MockRequestLog events={events} />}
        {view === "scorecard" && <ScoreCardDashboard />}
        {view === "resources" && <ResourceMap events={events} />}
        {view === "mcp" && <McpTraffic events={events} />}
      </main>
    </div>
  );
}
