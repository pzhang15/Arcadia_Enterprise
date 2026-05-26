import { useCallback, useEffect, useRef, useState } from "react";
import { useAgentStream } from "@/hooks/useAgentStream";
import {
  createSession,
  sendMessage as sendMessageApi,
  listSessions,
  getQuickActions,
} from "@/api/client";
import { cn, formatTime, timeAgo } from "@/lib/utils";
import type { StreamEvent, CommandEvent, QuickAction } from "@/types";
import type { MessageBlock, ToolCallState } from "@/types/agui";

const SERVICES = [
  { id: "it", label: "IT" },
  { id: "hr", label: "HR" },
  { id: "finance", label: "Finance" },
  { id: "engineering", label: "Engineering" },
  { id: "customer-support", label: "Customer Support" },
  { id: "compliance", label: "Compliance" },
] as const;

interface SessionItem {
  id: string;
  status: string;
  services: string[];
  created_at: number;
  message_count: number;
  last_message: string;
}

interface Props {
  events: StreamEvent[];
}

function ServiceToggle({
  id,
  label,
  active,
  onToggle,
}: {
  id: string;
  label: string;
  active: boolean;
  onToggle: (id: string) => void;
}) {
  return (
    <button
      onClick={() => onToggle(id)}
      className={cn(
        "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
        active
          ? "bg-accent-muted text-accent border border-accent/30"
          : "bg-surface-2 text-text-muted border border-border hover:border-border-hover hover:text-text-secondary",
      )}
    >
      {label}
    </button>
  );
}

function ExitCodeBadge({ code }: { code: number | undefined }) {
  if (code === undefined) return null;
  return (
    <span
      className={cn(
        "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-mono font-medium",
        code === 0
          ? "bg-success-muted text-success"
          : "bg-danger-muted text-danger",
      )}
    >
      {code}
    </span>
  );
}

function ToolCallCard({ tc }: { tc: ToolCallState }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="my-1.5 rounded-md border border-border bg-surface-1 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-surface-2 transition-colors"
      >
        <span className="text-text-muted text-[10px]">
          {tc.status === "running" ? "⟳" : "▸"}
        </span>
        <span className="font-mono text-xs text-text-secondary truncate flex-1">
          {tc.name}
        </span>
        <ExitCodeBadge code={tc.exit_code} />
      </button>
      {expanded && tc.result && (
        <pre className="px-3 py-2 border-t border-border text-[11px] font-mono text-text-muted overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
          {tc.result}
        </pre>
      )}
    </div>
  );
}

function MessageBubble({ msg }: { msg: MessageBlock }) {
  if (msg.role === "system") {
    return (
      <div className="flex justify-center my-2">
        <span className="text-xs text-text-muted px-3 py-1 bg-surface-2 rounded-full">
          {msg.content}
        </span>
      </div>
    );
  }

  if (msg.role === "user") {
    return (
      <div className="flex justify-end my-2">
        <div className="max-w-[80%] px-4 py-2.5 rounded-xl bg-accent text-white text-sm whitespace-pre-wrap">
          {msg.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start my-2">
      <div className="max-w-[85%]">
        <pre className="text-sm text-text-primary whitespace-pre-wrap font-sans leading-relaxed">
          {msg.content}
        </pre>
        {msg.toolCalls && msg.toolCalls.length > 0 && (
          <div className="mt-1">
            {msg.toolCalls.map((tc) => (
              <ToolCallCard key={tc.id} tc={tc} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function QuickActionCard({
  action,
  onSelect,
}: {
  action: QuickAction;
  onSelect: (action: QuickAction) => void;
}) {
  return (
    <button
      onClick={() => onSelect(action)}
      className="text-left p-3 rounded-lg border border-border bg-surface-1 hover:bg-surface-2 hover:border-border-hover transition-colors"
    >
      <span className="text-sm text-text-primary">{action.label}</span>
      <div className="mt-1 flex gap-1 flex-wrap">
        {action.services.map((s) => (
          <span
            key={s}
            className="text-[10px] px-1.5 py-0.5 rounded bg-surface-3 text-text-muted"
          >
            {s}
          </span>
        ))}
      </div>
    </button>
  );
}

function MountBadge({ path }: { path: string }) {
  const mount = inferMount(path);
  if (!mount) return null;

  const colorMap: Record<string, string> = {
    tickets: "text-mount-tickets",
    slack: "text-mount-slack",
    github: "text-mount-github",
    pagerduty: "text-mount-pagerduty",
    finance: "text-mount-finance",
    datadog: "text-mount-datadog",
    compliance: "text-mount-compliance",
    customers: "text-mount-customers",
  };

  return (
    <span
      className={cn(
        "text-[10px] px-1.5 py-0.5 rounded bg-surface-3 font-mono",
        colorMap[mount] || "text-text-muted",
      )}
    >
      {mount}
    </span>
  );
}

function inferMount(cmd: string): string | null {
  if (/ticket/i.test(cmd)) return "tickets";
  if (/slack/i.test(cmd)) return "slack";
  if (/github|git/i.test(cmd)) return "github";
  if (/pagerduty|incident/i.test(cmd)) return "pagerduty";
  if (/finance|expense|invoice|budget/i.test(cmd)) return "finance";
  if (/datadog|metric/i.test(cmd)) return "datadog";
  if (/compliance|audit|contract|policy/i.test(cmd)) return "compliance";
  if (/customer|account|escalation/i.test(cmd)) return "customers";
  return null;
}

function CommandEntry({ event }: { event: CommandEvent }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-border last:border-b-0 px-3 py-2">
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-text-muted font-mono">
          {formatTime(event.timestamp * 1000)}
        </span>
        <ExitCodeBadge code={event.exit_code} />
        <MountBadge path={event.command} />
      </div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="mt-1 w-full text-left"
      >
        <code className="text-xs font-mono text-text-secondary break-all">
          {event.command}
        </code>
      </button>
      {expanded && event.stdout && (
        <pre className="mt-1 text-[11px] font-mono text-text-muted bg-surface-0 rounded p-2 max-h-32 overflow-y-auto whitespace-pre-wrap">
          {event.stdout}
        </pre>
      )}
    </div>
  );
}

function StreamingIndicator() {
  return (
    <div className="flex items-center gap-2 my-3 px-1">
      <div className="flex gap-1">
        <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-fade" />
        <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-fade [animation-delay:300ms]" />
        <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse-fade [animation-delay:600ms]" />
      </div>
      <span className="text-xs text-text-muted">Agent is working...</span>
    </div>
  );
}

export default function AgentWorkspace({ events }: Props) {
  const {
    messages,
    isStreaming,
    error,
    sendMessage: streamSendMessage,
    addUserMessage,
    setMessages,
  } = useAgentStream();

  const [activeServices, setActiveServices] = useState<Set<string>>(
    new Set(["it"]),
  );
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [quickActions, setQuickActions] = useState<QuickAction[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    listSessions()
      .then(setSessions)
      .catch(() => {});
    getQuickActions()
      .then(setQuickActions)
      .catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleService = useCallback((id: string) => {
    setActiveServices((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const startNewConversation = useCallback(() => {
    setSessionId(null);
    setMessages([]);
  }, [setMessages]);

  const loadSession = useCallback(
    async (id: string) => {
      setSessionId(id);
      setMessages([]);
    },
    [setMessages],
  );

  const handleSend = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || sending) return;

      setInput("");
      setSending(true);
      addUserMessage(trimmed);

      try {
        let sid = sessionId;
        if (!sid) {
          const services = Array.from(activeServices);
          const session = await createSession(services);
          sid = session.id;
          setSessionId(sid);
        }

        try {
          await streamSendMessage(sid, trimmed);
        } catch {
          const fallback = await sendMessageApi(sid, trimmed);
          const assistantMsg: MessageBlock = {
            id: `fallback-${Date.now()}`,
            role: "assistant",
            content: fallback.reply,
            timestamp: Date.now(),
          };
          setMessages([...messages, { id: `user-fb-${Date.now()}`, role: "user", content: trimmed, timestamp: Date.now() }, assistantMsg]);
        }
      } catch (err) {
        const errorMsg =
          err instanceof Error ? err.message : "Failed to send message";
        const sysMsg: MessageBlock = {
          id: `err-${Date.now()}`,
          role: "system",
          content: errorMsg,
          timestamp: Date.now(),
        };
        setMessages([...messages, sysMsg]);
      } finally {
        setSending(false);
      }
    },
    [
      sessionId,
      activeServices,
      sending,
      addUserMessage,
      streamSendMessage,
      setMessages,
      messages,
    ],
  );

  const handleQuickAction = useCallback(
    (action: QuickAction) => {
      const services = new Set(action.services);
      setActiveServices(services);
      handleSend(action.task);
    },
    [handleSend],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend(input);
      }
    },
    [input, handleSend],
  );

  const sessionCommands = events.filter(
    (e): e is CommandEvent =>
      e.type === "command" && (!sessionId || e.session === sessionId),
  );

  return (
    <div className="flex h-full w-full overflow-hidden">
      {/* Left Panel */}
      <div className="w-[280px] shrink-0 border-r border-border bg-surface-1 flex flex-col">
        <div className="p-4 border-b border-border">
          <h2 className="text-sm font-semibold text-text-primary mb-3">
            Services
          </h2>
          <div className="flex flex-wrap gap-1.5">
            {SERVICES.map((s) => (
              <ServiceToggle
                key={s.id}
                id={s.id}
                label={s.label}
                active={activeServices.has(s.id)}
                onToggle={toggleService}
              />
            ))}
          </div>
        </div>
        <div className="p-3">
          <button
            onClick={startNewConversation}
            className="w-full py-2 px-3 rounded-md text-xs font-medium bg-accent text-white hover:bg-accent-hover transition-colors"
          >
            + New conversation
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2 pb-2">
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => loadSession(s.id)}
              className={cn(
                "w-full text-left p-2.5 rounded-md mb-1 transition-colors",
                sessionId === s.id
                  ? "bg-surface-3 border border-border-hover"
                  : "hover:bg-surface-2",
              )}
            >
              <div className="text-xs text-text-primary truncate">
                {s.last_message || "New session"}
              </div>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] text-text-muted">
                  {timeAgo(s.created_at)}
                </span>
                <span className="text-[10px] text-text-muted">
                  {s.message_count} msgs
                </span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Center Panel */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full">
              <h3 className="text-lg font-semibold text-text-primary mb-2">
                Arcadia Agent
              </h3>
              <p className="text-sm text-text-muted mb-6">
                Select services and describe your task
              </p>
              {quickActions.length > 0 && (
                <div className="grid grid-cols-2 gap-2 max-w-lg w-full">
                  {quickActions.map((a) => (
                    <QuickActionCard
                      key={a.id}
                      action={a}
                      onSelect={handleQuickAction}
                    />
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="max-w-3xl mx-auto">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} msg={msg} />
              ))}
              {isStreaming && <StreamingIndicator />}
              {error && (
                <div className="text-xs text-danger bg-danger-muted px-3 py-2 rounded-md my-2">
                  {error}
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        <div className="border-t border-border p-4 bg-surface-1">
          <div className="max-w-3xl mx-auto flex gap-2">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe a task for the agent..."
              rows={1}
              className="flex-1 resize-none rounded-lg border border-border bg-surface-0 px-4 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent transition-colors"
            />
            <button
              onClick={() => handleSend(input)}
              disabled={!input.trim() || sending || isStreaming}
              className={cn(
                "px-4 py-2.5 rounded-lg text-sm font-medium transition-colors",
                input.trim() && !sending && !isStreaming
                  ? "bg-accent text-white hover:bg-accent-hover"
                  : "bg-surface-2 text-text-muted cursor-not-allowed",
              )}
            >
              Send
            </button>
          </div>
        </div>
      </div>

      {/* Right Panel */}
      <div className="w-[380px] shrink-0 border-l border-border bg-surface-1 flex flex-col">
        <div className="p-4 border-b border-border flex items-center gap-2">
          <h2 className="text-sm font-semibold text-text-primary">
            Live Activity
          </h2>
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-success-muted text-success text-[10px] font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse-fade" />
            LIVE
          </span>
        </div>
        <div className="flex-1 overflow-y-auto">
          {sessionCommands.length === 0 ? (
            <div className="flex items-center justify-center h-full text-text-muted text-xs">
              No activity yet
            </div>
          ) : (
            sessionCommands.map((event, i) => (
              <CommandEntry key={`${event.timestamp}-${i}`} event={event} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}
