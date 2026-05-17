import { useCallback, useEffect, useRef, useState } from "react";
import { useEventStream } from "./hooks/useEventStream";
import {
  createSession,
  getSessionResult,
  getSessionStatus,
  listSessions,
  runSession,
} from "./api/client";
import ServiceConnector from "./components/ServiceConnector";
import SessionHistory from "./components/SessionHistory";
import TaskDialog, { type ChatMessage } from "./components/TaskDialog";
import LiveExecutionView from "./components/LiveExecutionView";
import ResultsSummary from "./components/ResultsSummary";
import type { AgentResult, QuickAction } from "./types";

interface SessionListEntry {
  id: string;
  status: string;
  task: string;
  created_at: number;
  completed_at: number | null;
}

export default function App() {
  const [selectedServices, setSelectedServices] = useState<Set<string>>(
    new Set(["it", "hr"]),
  );
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<string>("created");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [sessions, setSessions] = useState<SessionListEntry[]>([]);
  const { events, connected } = useEventStream("/events");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refreshSessions = useCallback(() => {
    listSessions()
      .then(setSessions)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

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

  const startPolling = useCallback(
    (sid: string) => {
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(async () => {
        try {
          const status = await getSessionStatus(sid);
          setSessionStatus(status.status);
          if (status.status === "completed") {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            const res = await getSessionResult(sid);
            setResult(res);
            addMessage(
              "agent",
              `Task complete in ${res.duration_s}s. Ran ${res.commands_run} commands across ${Object.keys(res.services_touched).length} services.`,
            );
            refreshSessions();
          } else if (status.status === "error") {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = null;
            addMessage("system", "Agent encountered an error.");
            refreshSessions();
          }
        } catch {
          /* ignore poll errors */
        }
      }, 500);
    },
    [addMessage, refreshSessions],
  );

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

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
        for (const svc of quickAction.services) {
          setSelectedServices((prev) => new Set([...prev, svc]));
        }
      }

      addMessage("user", task);
      setResult(null);
      setSessionStatus("created");

      try {
        addMessage("system", "Creating agent session...");
        const session = await createSession(services);
        setSessionId(session.id);
        addMessage(
          "system",
          `Session ${session.id} created. Starting agent...`,
        );

        await runSession(session.id, task);
        setSessionStatus("running");
        addMessage("system", `Agent started with ${services.length} service(s) connected.`);
        startPolling(session.id);
        refreshSessions();
      } catch (err) {
        addMessage(
          "system",
          `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        );
      }
    },
    [selectedServices, addMessage, startPolling, refreshSessions],
  );

  const handleToggleService = useCallback((service: string) => {
    setSelectedServices((prev) => {
      const next = new Set(prev);
      if (next.has(service)) next.delete(service);
      else next.add(service);
      return next;
    });
  }, []);

  const handleSelectSession = useCallback(
    async (id: string) => {
      setSessionId(id);
      try {
        const status = await getSessionStatus(id);
        setSessionStatus(status.status);
        if (status.status === "completed") {
          const res = await getSessionResult(id);
          setResult(res);
        } else {
          setResult(null);
        }
        setMessages([
          {
            id: `${Date.now()}-loaded`,
            role: "system",
            text: `Loaded session ${id}: ${status.task || "(no task)"}`,
            timestamp: Date.now(),
          },
        ]);
      } catch {
        addMessage("system", `Failed to load session ${id}`);
      }
    },
    [addMessage],
  );

  const isRunning = sessionStatus === "running";

  return (
    <div className="console-layout">
      <div className="console-panel" style={{ background: "var(--bg-secondary)" }}>
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
          <div style={{ margin: "20px 0 0" }}>
            <div className="sidebar-section" style={{ padding: "0 0 8px" }}>
              Session History
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
            {connected ? "Stream connected" : "Stream disconnected"}
            {events.length > 0 && (
              <span
                className="text-tertiary"
                style={{ marginLeft: "auto" }}
              >
                {events.length}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="console-panel" style={{ display: "flex", flexDirection: "column" }}>
        <div className="panel-header flex items-center gap-3">
          <span>Agent Workspace</span>
          {isRunning && <span className="badge info pulse">RUNNING</span>}
          {sessionStatus === "completed" && (
            <span className="badge success">COMPLETE</span>
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
        <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
          <div style={{ flex: "0 0 auto", maxHeight: "45%", overflow: "hidden" }}>
            <TaskDialog
              messages={messages}
              onSend={handleSend}
              disabled={isRunning}
            />
          </div>
          <div
            style={{
              flex: 1,
              borderTop: "1px solid var(--border)",
              overflow: "auto",
              minHeight: 0,
            }}
          >
            <LiveExecutionView events={events} sessionId={sessionId} />
          </div>
        </div>
      </div>

      <div
        className="console-panel"
        style={{ background: "var(--bg-secondary)" }}
      >
        <div className="panel-header">Results</div>
        <div className="panel-body">
          <ResultsSummary
            result={result}
            sessionId={sessionId}
            status={sessionStatus}
          />
        </div>
      </div>
    </div>
  );
}
