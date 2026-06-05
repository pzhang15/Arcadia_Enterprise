import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  ChevronLeft,
  Database,
  Eye,
  FolderTree,
  Hand,
  PauseCircle,
  Send,
  Sparkles,
  Wrench,
  XCircle,
} from "lucide-react";
import { useAgentStream } from "@/hooks/useAgentStream";
import {
  createSession,
  getSessionStatus,
  sendMessage as sendMessageApi,
} from "@/api/client";
import {
  getSessionRunSnapshot,
  hydrateSessionRun,
} from "@/lib/sessionRunStore";
import { cn, formatBytes } from "@/lib/utils";
import { useStickyScroll } from "@/lib/useStickyScroll";
import { stepColor } from "@/lib/stepColor";
import { findTemplate } from "@/lib/workspaceTemplates";
import {
  setInvestigationStatus,
  upsertInvestigation,
  useInvestigation,
} from "@/lib/investigationStore";
import type { StreamEvent, CommandEvent, OpEvent } from "@/types";
import type { MessageBlock } from "@/types/agui";
import { Badge, SectionLabel } from "@/components/ui";
import { RunTracePanel } from "@/components/run";
import {
  AuthorityBadge,
  SeverityBadge,
  StatusBadge,
  TriggerBadge,
} from "@/components/investigation/InvestigationBadges";

interface Props {
  events: StreamEvent[];
}

const ASSISTANT_AVATAR = (
  <div className="relative shrink-0">
    <div className="absolute -inset-0.5 rounded-xl bg-gradient-to-br from-accent/50 to-info/40 opacity-50 blur-sm" />
    <div className="relative grid h-7 w-7 place-items-center rounded-xl bg-gradient-to-br from-accent to-info text-white">
      <Sparkles size={13} />
    </div>
  </div>
);

function MessageBubble({
  msg,
  highlighted,
  onHover,
  onClick,
  msgRef,
}: {
  msg: MessageBlock;
  highlighted?: boolean;
  onHover?: (stepId: string | null) => void;
  onClick?: (stepId: string) => void;
  msgRef?: (el: HTMLDivElement | null) => void;
}) {
  const color = msg.stepId ? stepColor(msg.stepId) : null;

  if (msg.role === "system") {
    return (
      <div className="my-3 flex justify-center" ref={msgRef}>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 px-3 py-1 text-[11px] text-text-muted">
          {msg.content}
        </span>
      </div>
    );
  }

  if (msg.role === "user") {
    return (
      <div className="my-3 flex justify-end" ref={msgRef}>
        <div className="max-w-[80%] rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-[14px] text-white shadow-sm">
          <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={msgRef}
      onMouseEnter={() => msg.stepId && onHover?.(msg.stepId)}
      onMouseLeave={() => msg.stepId && onHover?.(null)}
      onClick={() => msg.stepId && onClick?.(msg.stepId)}
      className={cn(
        "my-3 flex items-start gap-3 rounded-xl px-2 py-1.5 transition-colors",
        msg.stepId && "cursor-pointer hover:bg-surface-1/50",
        highlighted && "bg-surface-1/80",
      )}
    >
      {ASSISTANT_AVATAR}
      <div className="min-w-0 max-w-[85%] flex-1">
        <div className="mb-1 flex items-center gap-2">
          <span className="text-[11px] font-medium text-text-muted">
            Arcadia Agent
          </span>
          {color && (
            <Badge
              tone="outline"
              size="xs"
              className={cn("font-mono", color.text)}
            >
              <span className={cn("h-1.5 w-1.5 rounded-full", color.bg)} />
              {msg.stepId}
            </Badge>
          )}
        </div>
        <div className="whitespace-pre-wrap text-[14px] leading-relaxed text-text-primary">
          {msg.content}
          {msg.isStreaming && (
            <span className="ml-0.5 inline-block h-3.5 w-[2px] -translate-y-px animate-pulse bg-accent align-middle" />
          )}
        </div>
      </div>
    </div>
  );
}

function StreamingIndicator() {
  return (
    <div className="my-4 flex items-center gap-3 px-1">
      {ASSISTANT_AVATAR}
      <div className="flex items-center gap-2">
        <div className="flex gap-1">
          <span className="h-1.5 w-1.5 animate-typing-dot rounded-full bg-accent" />
          <span className="h-1.5 w-1.5 animate-typing-dot rounded-full bg-accent [animation-delay:200ms]" />
          <span className="h-1.5 w-1.5 animate-typing-dot rounded-full bg-accent [animation-delay:400ms]" />
        </div>
        <span className="text-[12px] text-text-muted">Agent is reasoning…</span>
      </div>
    </div>
  );
}

export default function InvestigationDetail({ events }: Props) {
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const investigation = useInvestigation(urlSessionId || null);
  const template = investigation ? findTemplate(investigation.templateId) : null;

  const {
    messages,
    steps,
    runs,
    runOrder,
    toolCalls,
    isStreaming,
    error,
    sendMessage: streamSendMessage,
    addUserMessage,
    setMessages,
  } = useAgentStream(urlSessionId || null);

  const [sessionId, setSessionId] = useState<string | null>(urlSessionId || null);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [highlightedStepId, setHighlightedStepId] = useState<string | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [showResolveModal, setShowResolveModal] = useState<
    null | "resolved" | "escalated" | "cancelled"
  >(null);
  const [resolutionNote, setResolutionNote] = useState("");

  const messageRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const autostartRef = useRef(false);

  useEffect(() => {
    setSessionId(urlSessionId || null);
  }, [urlSessionId]);

  useEffect(() => {
    if (!urlSessionId) {
      setHistoryLoaded(true);
      return;
    }
    setHistoryLoaded(false);
    setHistoryError(null);
    let cancelled = false;
    hydrateSessionRun(urlSessionId)
      .then(() => getSessionStatus(urlSessionId).catch(() => null))
      .then((status) => {
        if (cancelled || !status || investigation) return;
        const snap = getSessionRunSnapshot(urlSessionId);
        const firstUser = snap.messages.find((m) => m.role === "user");
        const title =
          firstUser?.content?.slice(0, 80) ||
          `Investigation ${urlSessionId}`;
        upsertInvestigation({
          sessionId: urlSessionId,
          title,
          status:
            status.status === "completed"
              ? "needs_review"
              : status.status === "error"
                ? "escalated"
                : "running",
        });
      })
      .catch((e) => {
        if (cancelled) return;
        setHistoryError(
          e instanceof Error ? e.message : "Failed to load investigation",
        );
      })
      .finally(() => {
        if (!cancelled) setHistoryLoaded(true);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlSessionId]);

  const conversationScrollActive = messages.length > 0 || isStreaming;
  const {
    scrollRef: messagesScrollRef,
    endRef: messagesEndRef,
    atBottom,
    scrollToElement,
    jumpToLatest,
  } = useStickyScroll(conversationScrollActive, [messages, isStreaming]);

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
          const services = template?.services || [];
          const session = await createSession(services);
          sid = session.id;
          setSessionId(sid);
          if (urlSessionId !== sid) {
            navigate(`/investigations/${sid}`, { replace: true });
          }
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
          setMessages([
            ...messages,
            {
              id: `user-fb-${Date.now()}`,
              role: "user",
              content: trimmed,
              timestamp: Date.now(),
            },
            assistantMsg,
          ]);
        }
        upsertInvestigation({ sessionId: sid, status: "running" });
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
      template,
      sending,
      urlSessionId,
      navigate,
      addUserMessage,
      streamSendMessage,
      setMessages,
      messages,
    ],
  );

  // Autostart: if redirected here from Dispatch with autostart=1, send the brief
  useEffect(() => {
    if (autostartRef.current) return;
    if (!historyLoaded) return;
    if (searchParams.get("autostart") !== "1") return;
    const brief = searchParams.get("brief");
    if (!brief) return;
    autostartRef.current = true;
    setSearchParams({}, { replace: true });
    handleSend(brief);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [historyLoaded, searchParams]);

  const handleSelectStep = useCallback(
    (stepId: string) => {
      setHighlightedStepId(stepId);
      const step = steps[stepId];
      const msgId = step?.message_id;
      if (msgId) {
        const el = messageRefs.current.get(msgId);
        if (el) scrollToElement(el, "center");
      }
    },
    [steps, scrollToElement],
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

  const setMessageRef = (id: string) => (el: HTMLDivElement | null) => {
    if (el) messageRefs.current.set(id, el);
    else messageRefs.current.delete(id);
  };

  const orderedRuns = useMemo(
    () => runOrder.map((id) => runs[id]).filter(Boolean),
    [runOrder, runs],
  );

  const eventTotals = useMemo(() => {
    if (!sessionId) return { cmd: 0, op: 0, bytes: 0 };
    let cmd = 0;
    let op = 0;
    let bytes = 0;
    for (const e of events) {
      if ((e as { session?: string }).session && (e as { session?: string }).session !== sessionId) continue;
      if (e.type === "command") cmd++;
      else if (e.type === "op") {
        op++;
        bytes += (e as OpEvent).bytes || 0;
      }
    }
    return { cmd, op, bytes };
  }, [events, sessionId]);

  const lifecycleAction = useCallback(
    (status: "resolved" | "escalated" | "cancelled") => {
      if (!sessionId) return;
      setInvestigationStatus(sessionId, status, {
        resolution: resolutionNote.trim() || undefined,
        resolvedAt: Date.now(),
      });
      setShowResolveModal(null);
      setResolutionNote("");
      navigate("/");
    },
    [sessionId, resolutionNote, navigate],
  );

  if (!urlSessionId) {
    return (
      <div className="flex h-full items-center justify-center text-text-muted">
        Missing investigation ID
      </div>
    );
  }

  if (!historyLoaded) {
    return (
      <div className="flex h-full items-center justify-center text-text-muted">
        <div className="inline-flex items-center gap-2 text-[13px]">
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" />
          Loading investigation…
        </div>
      </div>
    );
  }

  if (historyError) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-text-muted">
        <AlertTriangle size={24} className="text-danger" />
        <div className="text-[13px]">{historyError}</div>
        <button
          onClick={() => navigate("/")}
          className="rounded-md border border-border bg-surface-2 px-3 py-1.5 text-[12px] hover:bg-surface-3"
        >
          Back to Inbox
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <header className="flex shrink-0 items-start gap-3 border-b border-border bg-surface-1/60 px-6 py-3 backdrop-blur-md">
        <button
          onClick={() => navigate("/")}
          className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md text-text-muted transition-colors hover:bg-surface-2 hover:text-text-primary"
          title="Back to Inbox"
        >
          <ChevronLeft size={14} />
        </button>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            {investigation && (
              <SeverityBadge severity={investigation.severity} size="xs" />
            )}
            <h1 className="truncate text-[14px] font-semibold tracking-tight text-text-primary">
              {investigation?.title || `Investigation ${urlSessionId}`}
            </h1>
            <span className="shrink-0 font-mono text-[10.5px] text-text-faint">
              {urlSessionId}
            </span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {investigation && (
              <>
                <StatusBadge status={investigation.status} size="xs" />
                <TriggerBadge
                  trigger={investigation.trigger}
                  triggerRef={investigation.triggerRef}
                  size="xs"
                />
                <AuthorityBadge authority={investigation.authority} size="xs" />
                {template && (
                  <span className="rounded border border-border bg-surface-2 px-1.5 py-0.5 font-mono text-[10px] text-text-muted">
                    {template.title}
                  </span>
                )}
              </>
            )}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {investigation?.status !== "resolved" && (
            <>
              <button
                onClick={() => {
                  setShowResolveModal("resolved");
                  setResolutionNote("");
                }}
                className="inline-flex h-8 items-center gap-1.5 rounded-md border border-success/30 bg-success-soft px-2.5 text-[12px] font-medium text-success transition-colors hover:bg-success-soft/80"
              >
                <CheckCircle2 size={12} />
                Resolve
              </button>
              <button
                onClick={() => {
                  setShowResolveModal("escalated");
                  setResolutionNote("");
                }}
                className="inline-flex h-8 items-center gap-1.5 rounded-md border border-danger/30 bg-danger-soft px-2.5 text-[12px] font-medium text-danger transition-colors hover:bg-danger-soft/80"
              >
                <AlertTriangle size={12} />
                Escalate
              </button>
            </>
          )}
          <button
            onClick={() => {
              if (sessionId) {
                setInvestigationStatus(sessionId, "needs_review");
              }
            }}
            className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-surface-2 px-2.5 text-[12px] font-medium text-text-secondary transition-colors hover:bg-surface-3 hover:text-text-primary"
          >
            <Hand size={12} />
            Flag for review
          </button>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[280px_minmax(420px,1fr)_minmax(420px,1fr)] overflow-hidden max-xl:grid-cols-[240px_minmax(380px,1fr)_minmax(380px,1fr)]">
        <ContextPane
          investigation={investigation}
          eventTotals={eventTotals}
          onOpenVfs={() => navigate(`/vfs?session=${urlSessionId}`)}
        />

        <section className="relative flex min-h-0 min-w-0 flex-col overflow-hidden border-r border-border bg-bg">
          <div
            ref={messagesScrollRef}
            data-testid="conversation-scroll"
            className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-6 py-5"
          >
            {messages.length === 0 ? (
              <div className="mx-auto flex min-h-full max-w-2xl flex-col justify-center text-center">
                <div className="relative mx-auto mb-5 grid h-14 w-14 place-items-center">
                  <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-accent/50 to-info/30 opacity-60 blur-xl" />
                  <div className="relative grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-accent to-info text-white shadow-lg">
                    <Sparkles size={22} />
                  </div>
                </div>
                <h2 className="mb-1.5 text-[18px] font-semibold tracking-tight text-text-primary">
                  Ready when you are
                </h2>
                <p className="mx-auto max-w-md text-[13px] text-text-muted">
                  Send the brief below and the agent will start streaming reasoning
                  steps into the trace panel on the right.
                </p>
                {investigation?.brief && (
                  <div className="mt-5 rounded-lg border border-border bg-surface-1 px-4 py-3 text-left">
                    <div className="mb-1 text-[10.5px] font-semibold uppercase tracking-wider text-text-muted">
                      Dispatch brief
                    </div>
                    <p className="text-[12.5px] leading-relaxed text-text-secondary">
                      {investigation.brief}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <div className="mx-auto max-w-2xl">
                {messages.map((msg) => (
                  <MessageBubble
                    key={msg.id}
                    msg={msg}
                    msgRef={setMessageRef(msg.id)}
                    highlighted={
                      msg.stepId !== undefined && msg.stepId === highlightedStepId
                    }
                    onHover={setHighlightedStepId}
                    onClick={(stepId) => setHighlightedStepId(stepId)}
                  />
                ))}
                {isStreaming && <StreamingIndicator />}
                {error && (
                  <div className="my-2 rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-[12px] text-danger">
                    {error}
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {!atBottom && messages.length > 0 && (
            <button
              onClick={jumpToLatest}
              className="absolute bottom-[110px] left-1/2 inline-flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-border bg-surface-2/95 px-3 py-1.5 text-[11.5px] font-medium text-text-secondary shadow-md backdrop-blur-md transition-colors hover:bg-surface-3 hover:text-text-primary"
            >
              <ArrowDown size={11} />
              Jump to latest
            </button>
          )}

          <div className="shrink-0 border-t border-border bg-surface-1/60 px-5 py-3.5 backdrop-blur-md">
            <div className="mx-auto max-w-2xl">
              <div className="group relative overflow-hidden rounded-2xl border border-border bg-surface-1 transition-colors focus-within:border-accent/40 focus-within:shadow-[0_0_0_3px_oklch(0.68_0.19_280/0.10)]">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Send a follow-up… (Enter to send, Shift+Enter for newline)"
                  rows={2}
                  className="block max-h-40 min-h-[60px] w-full resize-none bg-transparent px-4 py-3 pr-14 text-[14px] text-text-primary placeholder:text-text-muted focus:outline-none"
                />
                <button
                  onClick={() => handleSend(input)}
                  disabled={!input.trim() || sending || isStreaming}
                  className={cn(
                    "absolute bottom-2.5 right-2.5 grid h-9 w-9 place-items-center rounded-xl transition-all",
                    input.trim() && !sending && !isStreaming
                      ? "bg-accent text-white shadow-sm hover:bg-accent-hover"
                      : "cursor-not-allowed bg-surface-3 text-text-muted",
                  )}
                  aria-label="Send"
                >
                  {sending || isStreaming ? (
                    <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" />
                  ) : (
                    <ArrowUp size={15} strokeWidth={2.5} />
                  )}
                </button>
              </div>
            </div>
          </div>
        </section>

        <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden bg-surface-1/40">
          <RunTracePanel
            runs={orderedRuns}
            steps={steps}
            toolCalls={toolCalls}
            messages={messages}
            events={events}
            sessionId={sessionId}
            highlightedStepId={highlightedStepId}
            onHoverStep={setHighlightedStepId}
            onSelectStep={handleSelectStep}
          />
        </aside>
      </div>

      {showResolveModal && (
        <ResolveModal
          mode={showResolveModal}
          note={resolutionNote}
          onChange={setResolutionNote}
          onCancel={() => setShowResolveModal(null)}
          onConfirm={() => lifecycleAction(showResolveModal)}
        />
      )}
    </div>
  );
}

function ContextPane({
  investigation,
  eventTotals,
  onOpenVfs,
}: {
  investigation: ReturnType<typeof useInvestigation>;
  eventTotals: { cmd: number; op: number; bytes: number };
  onOpenVfs: () => void;
}) {
  const template = investigation ? findTemplate(investigation.templateId) : null;

  return (
    <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden border-r border-border bg-surface-1/40">
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
      <div className="border-b border-border p-4">
        <SectionLabel className="mb-2">Workspace</SectionLabel>
        {template ? (
          <>
            <div className="rounded-lg border border-border bg-surface-1 p-3">
              <div className="flex items-start gap-2">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-accent-soft text-accent">
                  <Database size={13} />
                </span>
                <div className="min-w-0 leading-tight">
                  <div className="text-[13px] font-semibold text-text-primary">
                    {template.title}
                  </div>
                  <div className="mt-0.5 text-[11px] text-text-muted">
                    {template.tagline}
                  </div>
                </div>
              </div>
            </div>
            <div className="mt-3 flex flex-col gap-1">
              {template.mounts.map((m) => (
                <div
                  key={m.path}
                  className="flex items-center justify-between rounded-md border border-border bg-surface-2 px-2 py-1"
                >
                  <span className="font-mono text-[11.5px] text-text-secondary">
                    {m.path}
                  </span>
                  <Badge
                    tone={m.mode === "rw" ? "warning" : "neutral"}
                    size="xs"
                    mono
                  >
                    {m.mode}
                  </Badge>
                </div>
              ))}
            </div>
            <button
              onClick={onOpenVfs}
              className="mt-2 inline-flex h-8 w-full items-center justify-center gap-1.5 rounded-md border border-border bg-surface-2 text-[11.5px] text-text-secondary transition-colors hover:bg-surface-3 hover:text-text-primary"
            >
              <FolderTree size={11} />
              Inspect workspace files
            </button>
          </>
        ) : (
          <div className="text-[11.5px] italic text-text-muted">
            No workspace template attached.
          </div>
        )}
      </div>

      <div className="border-b border-border p-4">
        <SectionLabel className="mb-2">Live counters</SectionLabel>
        <div className="grid grid-cols-2 gap-2">
          <CounterTile
            label="Commands"
            value={eventTotals.cmd}
            icon={<Wrench size={11} />}
          />
          <CounterTile
            label="VFS ops"
            value={eventTotals.op}
            icon={<Database size={11} />}
            hint={formatBytes(eventTotals.bytes)}
          />
        </div>
      </div>

      {investigation?.brief && (
        <div className="border-b border-border p-4">
          <SectionLabel className="mb-2">Brief</SectionLabel>
          <p className="text-[11.5px] leading-relaxed text-text-secondary">
            {investigation.brief}
          </p>
        </div>
      )}

      {template && (
        <div className="border-b border-border p-4">
          <SectionLabel className="mb-2">Budget caps</SectionLabel>
          <div className="space-y-1.5 text-[11px]">
            <BudgetLine
              label="Tokens"
              value={`${(template.budget.tokens / 1000).toFixed(0)}k`}
            />
            <BudgetLine
              label="Wallclock"
              value={`${template.budget.wallclockMin} min`}
            />
            <BudgetLine
              label="Tool calls"
              value={template.budget.toolCalls.toString()}
            />
          </div>
        </div>
      )}

      </div>
      <div className="shrink-0 border-t border-border p-4">
        <SectionLabel className="mb-2">Posture</SectionLabel>
        <div className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-[11px] leading-relaxed text-text-secondary">
          {investigation?.authority === "read_only" && (
            <div className="flex items-start gap-2">
              <Eye size={11} className="mt-0.5 shrink-0 text-accent" />
              Agent has <b className="text-text-primary">read-only</b> access to
              the mounts above. Any write attempt will be denied.
            </div>
          )}
          {investigation?.authority === "approve_writes" && (
            <div className="flex items-start gap-2">
              <PauseCircle size={11} className="mt-0.5 shrink-0 text-warning" />
              Writes are <b className="text-text-primary">queued for approval</b>.
              You'll see proposed changes here.
            </div>
          )}
          {investigation?.authority === "autonomous" && (
            <div className="flex items-start gap-2">
              <AlertTriangle size={11} className="mt-0.5 shrink-0 text-danger" />
              Agent operates <b className="text-text-primary">autonomously</b>.
              All actions are audited but executed without approval.
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}

function CounterTile({
  label,
  value,
  hint,
  icon,
}: {
  label: string;
  value: number;
  hint?: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="rounded-md border border-border bg-surface-2 px-2 py-1.5">
      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
        {icon}
        {label}
      </div>
      <div className="mt-0.5 font-mono text-[15px] font-semibold tabular-nums text-text-primary">
        {value}
      </div>
      {hint && (
        <div className="text-[10px] text-text-faint">{hint}</div>
      )}
    </div>
  );
}

function BudgetLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-[11px]">
      <span className="text-text-muted">{label}</span>
      <span className="font-mono text-text-primary">{value}</span>
    </div>
  );
}

function ResolveModal({
  mode,
  note,
  onChange,
  onCancel,
  onConfirm,
}: {
  mode: "resolved" | "escalated" | "cancelled";
  note: string;
  onChange: (v: string) => void;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const labels = {
    resolved: {
      title: "Mark as resolved",
      blurb:
        "Capture the outcome — root cause, what was changed, and any follow-up tasks. This becomes the investigation's final report.",
      confirm: "Resolve investigation",
      icon: <CheckCircle2 size={16} className="text-success" />,
      tone: "bg-success text-white hover:opacity-90",
    },
    escalated: {
      title: "Escalate to a human",
      blurb:
        "Tell the next responder what you've found and what's still ambiguous. Include the on-call team or person to page.",
      confirm: "Escalate",
      icon: <AlertTriangle size={16} className="text-danger" />,
      tone: "bg-danger text-white hover:opacity-90",
    },
    cancelled: {
      title: "Cancel investigation",
      blurb:
        "Mark as cancelled. The trace is preserved for audit but no further work will be done.",
      confirm: "Cancel",
      icon: <XCircle size={16} className="text-text-muted" />,
      tone: "bg-text-muted text-white hover:opacity-90",
    },
  }[mode];

  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/60 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-lg rounded-2xl border border-border bg-surface-1 p-5 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-center gap-2">
          {labels.icon}
          <h3 className="text-[14px] font-semibold text-text-primary">
            {labels.title}
          </h3>
        </div>
        <p className="mb-3 text-[12px] leading-relaxed text-text-muted">
          {labels.blurb}
        </p>
        <textarea
          value={note}
          onChange={(e) => onChange(e.target.value)}
          rows={5}
          placeholder="Root cause, actions taken, follow-ups, on-call hand-off…"
          className="block w-full resize-none rounded-md border border-border bg-surface-2 px-3 py-2 text-[12.5px] leading-relaxed text-text-primary placeholder:text-text-muted focus:border-accent"
        />
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-md border border-border bg-surface-2 px-3 py-1.5 text-[12px] text-text-secondary hover:bg-surface-3 hover:text-text-primary"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[12px] font-medium",
              labels.tone,
            )}
          >
            <Send size={12} />
            {labels.confirm}
          </button>
        </div>
      </div>
    </div>
  );
}
