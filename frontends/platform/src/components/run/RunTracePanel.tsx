import { useMemo } from "react";
import { useStickyScroll } from "@/lib/useStickyScroll";
import { Activity, GitBranch } from "lucide-react";
import { cn, formatBytes } from "@/lib/utils";
import { EmptyState, Badge } from "@/components/ui";
import { StepCard } from "./StepCard";
import { correlateEventsToSteps } from "@/lib/correlateEvents";
import type {
  AgentRun,
  MessageBlock,
  RunStep,
  ToolCallState,
} from "@/types/agui";
import type { OpEvent, StreamEvent } from "@/types";

interface Props {
  runs: AgentRun[];
  steps: Record<string, RunStep>;
  toolCalls: Record<string, ToolCallState>;
  messages: MessageBlock[];
  events: StreamEvent[];
  sessionId: string | null;
  highlightedStepId?: string | null;
  onHoverStep?: (id: string | null) => void;
  onSelectStep?: (id: string) => void;
}

export function RunTracePanel({
  runs,
  steps,
  toolCalls,
  messages,
  events,
  sessionId,
  highlightedStepId,
  onHoverStep,
  onSelectStep,
}: Props) {
  const stepList = useMemo(
    () =>
      Object.values(steps).sort((a, b) => a.started_at - b.started_at),
    [steps],
  );

  const { byStep } = useMemo(
    () => correlateEventsToSteps(events, stepList, sessionId),
    [events, stepList, sessionId],
  );

  const totals = useMemo(() => {
    const totalSteps = stepList.length;
    const totalTools = stepList.reduce(
      (acc, s) => acc + s.tool_call_ids.length,
      0,
    );
    let totalCmd = 0;
    let totalOp = 0;
    let totalBytes = 0;
    for (const arr of byStep.values()) {
      for (const e of arr) {
        if (e.type === "command") totalCmd++;
        else if (e.type === "op") {
          totalOp++;
          totalBytes += (e as OpEvent).bytes || 0;
        }
      }
    }
    return { totalSteps, totalTools, totalCmd, totalOp, totalBytes };
  }, [stepList, byStep]);

  const totalDuration = useMemo(() => {
    if (runs.length === 0) return 0;
    const first = Math.min(...runs.map((r) => r.started_at));
    const last = Math.max(
      ...runs.map((r) => r.ended_at ?? Date.now()),
    );
    return last - first;
  }, [runs]);

  const hasContent = stepList.length > 0 || runs.length > 0;
  const isStreaming = runs.some((r) => r.status === "running");
  const { scrollRef, endRef, atBottom, jumpToLatest } = useStickyScroll(
    hasContent,
    [stepList.length, isStreaming, totals.totalSteps],
  );

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <div className="flex h-14 shrink-0 items-center gap-2 border-b border-border px-4">
        <span className="grid h-6 w-6 place-items-center rounded-md bg-info-soft text-info">
          <GitBranch size={13} />
        </span>
        <div className="leading-tight">
          <h2 className="text-[13px] font-semibold text-text-primary">
            Run Trace
          </h2>
          <p className="text-[10.5px] text-text-muted">
            Reasoning → actions → observations
          </p>
        </div>
        {hasContent && (
          <Badge
            tone={runs.some((r) => r.status === "running") ? "info" : "neutral"}
            size="sm"
            dot={runs.some((r) => r.status === "running")}
            className="ml-auto"
          >
            {runs.some((r) => r.status === "running")
              ? "Streaming"
              : `${totals.totalSteps} step${totals.totalSteps === 1 ? "" : "s"}`}
          </Badge>
        )}
      </div>

      {hasContent && (
        <div className="grid shrink-0 grid-cols-4 gap-2 border-b border-border px-3 py-2.5">
          <MiniStat label="Steps" value={totals.totalSteps} />
          <MiniStat label="Tools" value={totals.totalTools} />
          <MiniStat label="VFS" value={totals.totalOp} hint={formatBytes(totals.totalBytes)} />
          <MiniStat
            label="Wall"
            value={totalDuration < 1000 ? `${totalDuration}ms` : `${(totalDuration / 1000).toFixed(1)}s`}
            mono
          />
        </div>
      )}

      <div className="relative min-h-0 flex-1">
        <div
          ref={scrollRef}
          data-testid="run-trace-scroll"
          className="h-full min-h-0 overflow-y-auto overscroll-contain px-3 py-3"
        >
          {!hasContent ? (
            <EmptyState
              icon={<Activity size={20} />}
              title="No active run"
              description="Once you send a task, each reasoning step the agent takes — with the tool calls and VFS ops it triggers — will stream into this trace."
              size="md"
            />
          ) : (
            <div className="flex flex-col gap-2">
              {stepList.map((step, idx) => {
                const stepTools = step.tool_call_ids
                  .map((id) => toolCalls[id])
                  .filter(Boolean);
                const stepEvents = byStep.get(step.id) || [];
                const stepMessage = step.message_id
                  ? messages.find((m) => m.id === step.message_id)
                  : undefined;
                return (
                  <StepCard
                    key={step.id}
                    index={idx}
                    step={step}
                    toolCalls={stepTools}
                    events={stepEvents}
                    messagePreview={stepMessage?.content}
                    highlighted={highlightedStepId === step.id}
                    onHoverStep={onHoverStep}
                    onSelectStep={onSelectStep}
                  />
                );
              })}
              <div ref={endRef} className="h-px shrink-0" aria-hidden />
            </div>
          )}
        </div>
        {!atBottom && hasContent && (
          <button
            type="button"
            onClick={jumpToLatest}
            className="absolute bottom-3 left-1/2 z-10 inline-flex -translate-x-1/2 items-center gap-1.5 rounded-full border border-border bg-surface-2/95 px-3 py-1.5 text-[11px] font-medium text-text-secondary shadow-md backdrop-blur-md transition-colors hover:bg-surface-3 hover:text-text-primary"
          >
            Jump to latest
          </button>
        )}
      </div>
    </div>
  );
}

function MiniStat({
  label,
  value,
  hint,
  mono,
}: {
  label: string;
  value: number | string;
  hint?: string;
  mono?: boolean;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface-1 px-2.5 py-1.5">
      <div className="text-[9.5px] font-semibold uppercase tracking-wider text-text-muted">
        {label}
      </div>
      <div
        className={cn(
          "mt-0.5 text-[15px] font-semibold leading-none text-text-primary tabular-nums",
          mono && "font-mono",
        )}
      >
        {value}
      </div>
      {hint && (
        <div className="mt-0.5 text-[9.5px] text-text-faint">{hint}</div>
      )}
    </div>
  );
}
