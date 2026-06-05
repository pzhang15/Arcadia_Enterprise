import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useOutletContext } from "react-router-dom";
import {
  FlaskConical,
  GitFork,
  Link2,
  Loader2,
  Send,
  ShieldAlert,
  ShieldCheck,
  Square,
  Terminal,
  X,
} from "lucide-react";
import { useAgentStream } from "@/hooks/useAgentStream";
import {
  branchWorkspace,
  createConsoleSession,
  testRunWorkspace,
} from "@/api/client";
import {
  refreshWorkspaceDetail,
  selectActiveDetail,
  setActiveWorkspace,
  setWorkspaceSession,
  upsertWorkspaceDetail,
  useConsoleStore,
} from "@/lib/consoleStore";
import type { AgentRun } from "@/types/agui";
import type { TestRunResult } from "@/types/console";
import { cn } from "@/lib/utils";
import { RunTracePanel } from "@/components/run";
import { EffectClassTag, LiveWorldPanel } from "@/components/console";
import { Button } from "@/components/ui";
import type { ConsoleOutletCtx } from "./ConsoleLayout";
import { NoWorkspace } from "./NoWorkspace";

export default function RunPage() {
  const { events } = useOutletContext<ConsoleOutletCtx>();
  const store = useConsoleStore();
  const navigate = useNavigate();
  const active = selectActiveDetail(store);
  const activeId = active?.id ?? null;

  const [prompt, setPrompt] = useState("");
  const [showConnect, setShowConnect] = useState(false);
  const [testResult, setTestResult] = useState<TestRunResult | null>(null);
  const [testing, setTesting] = useState(false);
  const creatingRef = useRef<string | null>(null);
  // Session id is derived from the persisted workspace->session map, so
  // switching workspaces reattaches the existing session (and its hydrated
  // history + reasoning) instead of minting a fresh, empty one.
  const sessionId = activeId ? store.sessionByWorkspace[activeId] ?? null : null;
  const stream = useAgentStream(sessionId);

  useEffect(() => {
    if (!active || active.status !== "ready" || sessionId) return;
    if (creatingRef.current === active.id) return;
    creatingRef.current = active.id;
    createConsoleSession(active.id)
      .then((s) => setWorkspaceSession(active.id, s.id))
      .catch(() => {})
      .finally(() => {
        if (creatingRef.current === active.id) creatingRef.current = null;
      });
  }, [active?.status, active?.id, sessionId]);

  const runList = useMemo<AgentRun[]>(
    () => stream.runOrder.map((id) => stream.runs[id]).filter(Boolean),
    [stream.runOrder, stream.runs],
  );

  if (!active) return <NoWorkspace />;

  function run() {
    if (!sessionId || !prompt.trim() || stream.isStreaming) return;
    const text = prompt.trim();
    setPrompt("");
    stream.addUserMessage(text);
    stream.sendMessage(sessionId, text).then(() => {
      if (activeId) refreshWorkspaceDetail(activeId);
    });
  }

  async function branchFromHere() {
    if (!activeId) return;
    const detail = await branchWorkspace(activeId, "fork");
    upsertWorkspaceDetail(detail);
    setActiveWorkspace(detail.id);
  }

  async function dispatchTestAgent() {
    if (!activeId || testing) return;
    setTesting(true);
    try {
      const result = await testRunWorkspace(activeId);
      setTestResult(result);
      refreshWorkspaceDetail(activeId);
    } finally {
      setTesting(false);
    }
  }

  const ready = active.status === "ready";

  return (
    <div className="flex h-full flex-col">
      <div className="flex shrink-0 items-center gap-2 border-b border-border bg-surface-0 px-3 py-2">
        <span className="flex items-center gap-1.5 text-[12px] text-text-secondary">
          <Terminal size={14} className="text-text-muted" />
          {active.name}
        </span>
        <span className="font-mono text-[10px] text-text-faint">
          {sessionId ? `session ${sessionId}` : ready ? "connecting…" : "not ready"}
        </span>
        <div className="ml-auto flex items-center gap-1.5">
          <Button
            size="sm"
            variant="secondary"
            onClick={dispatchTestAgent}
            disabled={!ready || testing}
            title="Dispatch a deterministic testing agent to validate the workspace (mounts, permissions, capture)"
          >
            {testing ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <FlaskConical size={13} />
            )}
            Test agent
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setShowConnect((v) => !v)}
            title="Connect your own agent"
          >
            <Link2 size={13} /> Connect agent
          </Button>
          <Button
            size="sm"
            variant="secondary"
            onClick={branchFromHere}
            disabled={!ready}
            title="Fork the current overlay into a new branch"
          >
            <GitFork size={13} /> Branch from here
          </Button>
          {stream.isStreaming && (
            <Button size="sm" variant="danger" onClick={stream.abort}>
              <Square size={12} /> Kill
            </Button>
          )}
        </div>
      </div>

      {showConnect && (
        <div className="shrink-0 border-b border-border bg-surface-1 px-3 py-2.5">
          <p className="mb-1.5 text-[11px] text-text-muted">
            Primary path — point your agent at this workspace's VFS-as-MCP
            endpoint{" "}
            <span className="rounded bg-surface-3 px-1 font-mono text-[10px] text-text-faint">
              preview
            </span>
            :
          </p>
          <pre className="overflow-x-auto rounded-lg border border-border bg-surface-0 p-2.5 font-mono text-[11px] text-text-secondary">
{`{
  "mcpServers": {
    "mirage": { "url": "http://localhost:8080/mcp/console/${active.id}" }
  }
}`}
          </pre>
        </div>
      )}

      {testResult && (
        <div className="shrink-0 border-b border-border bg-surface-1 px-3 py-2.5">
          <div className="mb-2 flex items-center gap-2">
            <FlaskConical size={14} className="text-simulated" />
            <span className="text-[12px] font-medium text-text-secondary">
              Testing agent
            </span>
            <span
              className={cn(
                "rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase",
                testResult.ok
                  ? "bg-success-soft text-success"
                  : "bg-danger-soft text-danger",
              )}
            >
              {testResult.ok ? "pass" : "fail"}
            </span>
            <span className="font-mono text-[10px] text-text-muted">
              {testResult.steps.length} steps · {testResult.captured_writes} captured
            </span>
            <button
              onClick={() => setTestResult(null)}
              className="ml-auto grid h-6 w-6 place-items-center rounded-md text-text-muted hover:bg-surface-3 hover:text-text-primary"
            >
              <X size={13} />
            </button>
          </div>
          <div className="flex flex-col gap-1">
            {testResult.permissions.map((p) => (
              <div
                key={p.prefix}
                className="flex items-center gap-2 rounded-md border border-border bg-surface-0 px-2 py-1.5"
              >
                {p.enforced ? (
                  <ShieldCheck size={13} className="shrink-0 text-success" />
                ) : (
                  <ShieldAlert size={13} className="shrink-0 text-danger" />
                )}
                <span className="font-mono text-[11px] text-text-secondary">
                  {p.prefix}
                </span>
                <span className="font-mono text-[10px] uppercase text-text-faint">
                  {p.mode}
                </span>
                <EffectClassTag effectClass={p.effect_class} />
                <span className="ml-auto font-mono text-[10px] text-text-muted">
                  {p.writable ? "write captured" : "write blocked"}
                  {p.enforced ? "" : " · permission NOT enforced"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-[1fr_360px]">
        <div className="flex min-h-0 flex-col border-r border-border">
          <div className="min-h-0 flex-1 overflow-hidden">
            <RunTracePanel
              runs={runList}
              steps={stream.steps}
              toolCalls={stream.toolCalls}
              messages={stream.messages}
              events={events}
              sessionId={sessionId}
            />
          </div>
          <div className="shrink-0 border-t border-border bg-surface-1 p-2.5">
            <div className="flex items-end gap-2">
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run();
                }}
                rows={2}
                disabled={!ready}
                placeholder={
                  ready
                    ? "Task the agent… (e.g. triage /tickets and write a summary to /scratch/triage.md)"
                    : "Stand up the workspace to run an agent."
                }
                className="scrollbar-thin min-h-0 flex-1 resize-none rounded-lg border border-border bg-surface-0 px-3 py-2 text-[13px] text-text-primary outline-none focus-visible:border-accent disabled:opacity-50"
              />
              <Button
                variant="primary"
                onClick={run}
                disabled={!ready || !sessionId || !prompt.trim() || stream.isStreaming}
              >
                {stream.isStreaming ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Send size={14} />
                )}
                Run
              </Button>
            </div>
          </div>
        </div>

        <div className="min-h-0 bg-surface-0">
          <LiveWorldPanel vfsOps={stream.vfsOps} mounts={active.mounts} />
        </div>
      </div>
    </div>
  );
}
