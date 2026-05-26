import { useCallback, useEffect, useState } from "react";
import { useEventStream } from "./hooks/useEventStream";
import CommandTimeline from "./components/CommandTimeline";
import MockRequestLog from "./components/MockRequestLog";
import ScoreCardDashboard from "./components/ScoreCardDashboard";
import ResourceMap from "./components/ResourceMap";
import McpTraffic from "./components/McpTraffic";
import TraceExplorer from "./components/TraceExplorer";
import ITHelpdesk from "./components/ITHelpdesk";
import HRDashboard from "./components/HRDashboard";
import FinanceDashboard from "./components/FinanceDashboard";
import EngineeringDashboard from "./components/EngineeringDashboard";
import CustomerSupport from "./components/CustomerSupport";
import ComplianceDashboard from "./components/ComplianceDashboard";
import ServiceConnector from "./components/ServiceConnector";
import SessionHistory from "./components/SessionHistory";
import TaskDialog, { type ChatMessage } from "./components/TaskDialog";
import LiveExecutionView from "./components/LiveExecutionView";
import {
  createSession,
  getSessionHistory,
  listSessions,
  sendMessage,
} from "./api/client";
import type { QuickAction } from "./types";

type View =
  | "it"
  | "hr"
  | "finance"
  | "engineering"
  | "customers"
  | "compliance"
  | "console"
  | "timeline"
  | "mcp"
  | "requests"
  | "resources"
  | "traces"
  | "scorecard";

interface NavItem {
  id: View;
  label: string;
  icon: string;
  section: string;
}

const NAV: NavItem[] = [
  { id: "it", label: "IT Helpdesk", icon: "ticket", section: "Portal" },
  { id: "hr", label: "HR & People", icon: "people", section: "Portal" },
  { id: "finance", label: "Finance", icon: "finance", section: "Portal" },
  { id: "engineering", label: "Engineering", icon: "engineering", section: "Portal" },
  { id: "customers", label: "Customer Support", icon: "customers", section: "Portal" },
  { id: "compliance", label: "Compliance", icon: "compliance", section: "Portal" },
  { id: "console", label: "Agent Console", icon: "console", section: "Console" },
  { id: "timeline", label: "Command Timeline", icon: "timeline", section: "Observability" },
  { id: "mcp", label: "MCP Traffic", icon: "mcp", section: "Observability" },
  { id: "requests", label: "Request Log", icon: "requests", section: "Observability" },
  { id: "resources", label: "Resource Map", icon: "resources", section: "Observability" },
  { id: "traces", label: "Trace Explorer", icon: "traces", section: "Observability" },
  { id: "scorecard", label: "Scorecard", icon: "scorecard", section: "Observability" },
];

interface SessionListEntry {
  id: string;
  status: string;
  services: string[];
  created_at: number;
  message_count: number;
  last_message: string;
}

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
    case "traces":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M2 4h5M4 8h8M6 12h7" />
          <circle cx="13" cy="4" r="1" fill="currentColor" />
          <circle cx="12" cy="8" r="1" fill="currentColor" />
          <circle cx="13" cy="12" r="1" fill="currentColor" />
        </svg>
      );
    case "ticket":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="2" y="3" width="12" height="10" rx="2" />
          <path d="M2 7h12" />
          <path d="M5 10h6" />
        </svg>
      );
    case "people":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="8" cy="5" r="2.5" />
          <path d="M3 14c0-2.8 2.2-5 5-5s5 2.2 5 5" />
        </svg>
      );
    case "finance":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M8 2v12M5 4.5C5 3.7 6.3 3 8 3s3 .7 3 1.5S9.7 6 8 6 5 6.7 5 7.5 6.3 9 8 9s3 .7 3 1.5S9.7 12 8 12s-3-.7-3-1.5" />
        </svg>
      );
    case "engineering":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M5.5 2L3 8l2.5 6M10.5 2L13 8l-2.5 6M9 2L7 14" />
        </svg>
      );
    case "customers":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M14 12.5c0-1.4-1.8-2.5-4-2.5-1 0-1.9.2-2.6.6M6 12.5c0-1.4-1.8-2.5-4-2.5" />
          <circle cx="10" cy="6" r="2" />
          <circle cx="4.5" cy="7.5" r="1.5" />
        </svg>
      );
    case "compliance":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="3" y="2" width="10" height="12" rx="1" />
          <path d="M6 6h4M6 8.5h4M6 11h2" />
        </svg>
      );
    case "console":
      return (
        <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <rect x="2" y="2" width="12" height="12" rx="2" />
          <path d="M5 6l2.5 2.5L5 11M9 11h3" />
        </svg>
      );
    default:
      return null;
  }
}

export default function App() {
  const [view, setView] = useState<View>("it");
  const { events, connected, clear } = useEventStream("/events");

  const [selectedServices, setSelectedServices] = useState<Set<string>>(
    new Set(["it", "hr"]),
  );
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<SessionListEntry[]>([]);

  useEffect(() => {
    listSessions().then(setSessions).catch(() => {});
  }, []);

  const addMessage = useCallback(
    (role: ChatMessage["role"], text: string) => {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          role,
          text,
          timestamp: Date.now(),
        },
      ]);
    },
    [],
  );

  const handleSend = useCallback(
    async (task: string, quickAction?: QuickAction) => {
      const services = quickAction
        ? quickAction.services
        : [...selectedServices];
      if (services.length === 0) {
        addMessage("system", "Please connect at least one service first.");
        return;
      }

      if (quickAction) {
        setSelectedServices((prev) => {
          const next = new Set(prev);
          for (const s of quickAction.services) next.add(s);
          return next;
        });
      }

      addMessage("user", task);
      setIsProcessing(true);

      try {
        let sid = sessionId;
        if (!sid) {
          addMessage("system", "Creating session...");
          const session = await createSession(services);
          sid = session.id;
          setSessionId(sid);
          if (!session.has_workspace) {
            addMessage(
              "system",
              "Note: workspace could not be built. Make sure seed data is generated.",
            );
          }
        }

        const resp = await sendMessage(sid, task);
        addMessage("agent", resp.reply);
        listSessions().then(setSessions).catch(() => {});
      } catch (err) {
        addMessage(
          "system",
          `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        );
      } finally {
        setIsProcessing(false);
      }
    },
    [selectedServices, sessionId, addMessage],
  );

  const handleToggleService = useCallback((service: string) => {
    setSelectedServices((prev) => {
      const next = new Set(prev);
      if (next.has(service)) next.delete(service);
      else next.add(service);
      return next;
    });
  }, []);

  const handleNewSession = useCallback(() => {
    setSessionId(null);
    setMessages([]);
    setIsProcessing(false);
  }, []);

  const handleSelectSession = useCallback(
    async (id: string) => {
      setSessionId(id);
      setIsProcessing(false);
      try {
        const history = await getSessionHistory(id);
        setMessages(
          history.map((e, i) => ({
            id: `${e.timestamp}-${i}`,
            role: (e.role === "assistant" ? "agent" : e.role) as ChatMessage["role"],
            text: e.content,
            timestamp: e.timestamp * 1000,
          })),
        );
      } catch {
        setMessages([]);
        addMessage("system", `Loaded session ${id}`);
      }
    },
    [addMessage],
  );

  let currentSection = "";

  const renderContent = () => {
    switch (view) {
      case "it":
        return <ITHelpdesk />;
      case "hr":
        return <HRDashboard />;
      case "finance":
        return <FinanceDashboard />;
      case "engineering":
        return <EngineeringDashboard />;
      case "customers":
        return <CustomerSupport />;
      case "compliance":
        return <ComplianceDashboard />;
      case "timeline":
        return <CommandTimeline events={events} onClear={clear} />;
      case "requests":
        return <MockRequestLog events={events} />;
      case "scorecard":
        return <ScoreCardDashboard />;
      case "resources":
        return <ResourceMap events={events} />;
      case "mcp":
        return <McpTraffic events={events} />;
      case "traces":
        return <TraceExplorer />;
      case "console":
        return (
          <div className="console-layout">
            <div
              className="console-panel"
              style={{ background: "var(--bg-secondary)" }}
            >
              <div className="panel-header flex items-center gap-2">
                <span>Services</span>
              </div>
              <div className="panel-body">
                <ServiceConnector
                  selected={selectedServices}
                  onToggle={handleToggleService}
                />
                <div style={{ marginTop: 16 }}>
                  <button
                    className="filter-btn"
                    style={{ width: "100%" }}
                    onClick={handleNewSession}
                  >
                    + New conversation
                  </button>
                </div>
                <div style={{ margin: "20px 0 0" }}>
                  <div className="sidebar-section" style={{ padding: "0 0 8px" }}>
                    History
                  </div>
                  <SessionHistory
                    sessions={sessions}
                    activeId={sessionId}
                    onSelect={handleSelectSession}
                  />
                </div>
              </div>
            </div>

            <div
              className="console-panel"
              style={{ display: "flex", flexDirection: "column" }}
            >
              <div className="panel-header flex items-center gap-3">
                <span>Agent Workspace</span>
                {isProcessing && (
                  <span className="badge info pulse">THINKING</span>
                )}
                {sessionId && (
                  <span
                    className="mono text-sm text-tertiary"
                    style={{ marginLeft: "auto" }}
                  >
                    {sessionId}
                  </span>
                )}
              </div>
              <div
                style={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  minHeight: 0,
                }}
              >
                <div style={{ flex: 1, overflow: "hidden" }}>
                  <TaskDialog
                    messages={messages}
                    onSend={handleSend}
                    disabled={isProcessing}
                  />
                </div>
              </div>
            </div>

            <div
              className="console-panel"
              style={{ background: "var(--bg-secondary)", display: "flex", flexDirection: "column" }}
            >
              <div className="panel-header">Live Activity</div>
              <div style={{ flex: 1, overflow: "auto" }}>
                <LiveExecutionView events={events} sessionId={sessionId} />
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="app-layout">
      <nav className="sidebar">
        <div className="sidebar-logo">
          Arcadia <span>platform</span>
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
      <main className={view === "console" ? "main-content console-main" : "main-content"}>
        {renderContent()}
      </main>
    </div>
  );
}
