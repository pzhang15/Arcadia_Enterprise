import { useCallback, useEffect, useState } from "react";
import { useEventStream } from "./hooks/useEventStream";
import {
  createSession,
  getConfig,
  getSessionHistory,
  listSessions,
  sendMessage,
} from "./api/client";
import ServiceConnector from "./components/ServiceConnector";
import SessionHistory from "./components/SessionHistory";
import TaskDialog, { type ChatMessage } from "./components/TaskDialog";
import LiveExecutionView from "./components/LiveExecutionView";
import type { QuickAction } from "./types";

interface SessionListEntry {
  id: string;
  status: string;
  services: string[];
  created_at: number;
  message_count: number;
  last_message: string;
}

export default function App() {
  const [selectedServices, setSelectedServices] = useState<Set<string>>(
    new Set(["it", "hr"]),
  );
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sessions, setSessions] = useState<SessionListEntry[]>([]);
  const [hasApiKey, setHasApiKey] = useState(true);
  const { events, connected } = useEventStream("/events");

  useEffect(() => {
    listSessions().then(setSessions).catch(() => {});
    getConfig()
      .then((cfg) => setHasApiKey(cfg.has_api_key))
      .catch(() => {});
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

  return (
    <div className="console-layout">
      <div
        className="console-panel"
        style={{ background: "var(--bg-secondary)" }}
      >
        <div className="panel-header flex items-center gap-2">
          <span>Mirage</span>
          <span
            style={{
              fontSize: 11,
              color: "var(--text-tertiary)",
              fontWeight: 400,
              padding: "2px 6px",
              background: "var(--bg-tertiary)",
              borderRadius: "var(--radius-sm)",
            }}
          >
            console
          </span>
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
        <div
          style={{
            padding: "12px 16px",
            borderTop: "1px solid var(--border)",
          }}
        >
          <div className="connection-status">
            <div
              className={`connection-dot ${connected ? "connected" : ""}`}
            />
            {connected ? "Stream connected" : "Disconnected"}
          </div>
          {!hasApiKey && (
            <div
              style={{
                marginTop: 8,
                fontSize: 11,
                color: "var(--yellow)",
              }}
            >
              OPENAI_API_KEY not set
            </div>
          )}
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
}
