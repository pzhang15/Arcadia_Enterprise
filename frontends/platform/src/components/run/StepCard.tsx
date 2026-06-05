import { useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleX,
  Database,
  Globe,
  Loader2,
  MessageSquare,
  Terminal,
  Wrench,
} from "lucide-react";
import { cn, formatBytes } from "@/lib/utils";
import { Badge } from "@/components/ui";
import { ReasoningBlock } from "./ReasoningBlock";
import { ToolCallRow } from "./ToolCallRow";
import { stepColor } from "@/lib/stepColor";
import type {
  RunStep,
  ToolCallState,
} from "@/types/agui";
import type {
  CommandEvent,
  McpToolCallEvent,
  MockRequestEvent,
  OpEvent,
  StreamEvent,
} from "@/types";

interface Props {
  index: number;
  step: RunStep;
  toolCalls: ToolCallState[];
  events: StreamEvent[];
  messagePreview?: string;
  highlighted?: boolean;
  onHoverStep?: (id: string | null) => void;
  onSelectStep?: (id: string) => void;
}

function durationLabel(step: RunStep): string {
  const end = step.ended_at ?? Date.now();
  const ms = end - step.started_at;
  if (ms < 1000) return `${Math.max(0, Math.round(ms))}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function StepCard({
  index,
  step,
  toolCalls,
  events,
  messagePreview,
  highlighted,
  onHoverStep,
  onSelectStep,
}: Props) {
  const [open, setOpen] = useState(true);
  const color = useMemo(() => stepColor(step.id), [step.id]);

  const counts = useMemo(() => {
    let cmd = 0;
    let op = 0;
    let mcp = 0;
    let http = 0;
    let bytes = 0;
    for (const e of events) {
      if (e.type === "command") cmd++;
      else if (e.type === "op") {
        op++;
        bytes += (e as OpEvent).bytes || 0;
      } else if (e.type === "mcp_tool_call") mcp++;
      else if (e.type === "mock_request") http++;
    }
    return { cmd, op, mcp, http, bytes };
  }, [events]);

  const StatusIcon =
    step.status === "running"
      ? Loader2
      : step.status === "error"
        ? CircleX
        : CheckCircle2;
  const statusColor =
    step.status === "running"
      ? "text-info"
      : step.status === "error"
        ? "text-danger"
        : "text-success";

  return (
    <div
      onMouseEnter={() => onHoverStep?.(step.id)}
      onMouseLeave={() => onHoverStep?.(null)}
      onClick={() => onSelectStep?.(step.id)}
      className={cn(
        "group relative overflow-hidden rounded-xl border bg-surface-1 transition-all duration-150",
        highlighted
          ? "border-border-hover shadow-md"
          : "border-border hover:border-border-hover",
      )}
    >
      <span
        className={cn(
          "absolute inset-y-0 left-0 w-[3px]",
          color.rail,
          step.status === "running" && "animate-pulse",
        )}
      />

      <button
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className="flex w-full items-center gap-3 px-4 py-2.5 text-left"
      >
        <span
          className={cn(
            "grid h-6 w-6 shrink-0 place-items-center rounded-md font-mono text-[10.5px] font-semibold",
            color.soft,
            color.text,
          )}
        >
          {index + 1}
        </span>
        <div className="min-w-0 flex-1 leading-tight">
          <div className="flex items-center gap-2">
            <StatusIcon
              size={12}
              className={cn(
                "shrink-0",
                statusColor,
                step.status === "running" && "animate-spin",
              )}
            />
            <span className="truncate text-[13px] font-semibold text-text-primary">
              {step.name}
            </span>
          </div>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10.5px] text-text-muted">
            <span className="font-mono">{durationLabel(step)}</span>
            {toolCalls.length > 0 && (
              <span className="inline-flex items-center gap-1">
                <span className="text-text-faint">·</span>
                <Wrench size={9} /> {toolCalls.length} call
                {toolCalls.length === 1 ? "" : "s"}
              </span>
            )}
            {counts.cmd > 0 && (
              <span className="inline-flex items-center gap-1">
                <span className="text-text-faint">·</span>
                <Terminal size={9} /> {counts.cmd} cmd{counts.cmd === 1 ? "" : "s"}
              </span>
            )}
            {counts.op > 0 && (
              <span className="inline-flex items-center gap-1">
                <span className="text-text-faint">·</span>
                <Database size={9} /> {counts.op} VFS ·{" "}
                {formatBytes(counts.bytes)}
              </span>
            )}
            {counts.mcp > 0 && (
              <span className="inline-flex items-center gap-1">
                <span className="text-text-faint">·</span>
                <Wrench size={9} /> {counts.mcp} MCP
              </span>
            )}
          </div>
        </div>
        <span className="shrink-0 text-text-muted">
          {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        </span>
      </button>

      {open && (
        <div className="border-t border-border bg-surface-1/50 px-4 py-3">
          {(step.reasoning || step.reasoning_streaming) && (
            <ReasoningBlock
              text={step.reasoning}
              streaming={step.reasoning_streaming}
              accentText={color.text}
            />
          )}

          {toolCalls.length > 0 && (
            <div className="my-2 flex flex-col gap-1">
              {toolCalls.map((tc) => (
                <ToolCallRow key={tc.id} tc={tc} />
              ))}
            </div>
          )}

          {events.length > 0 && (
            <EventGroup events={events} />
          )}

          {messagePreview && (
            <div className="mt-2 flex gap-2 rounded-md border border-border bg-surface-0 px-3 py-2">
              <MessageSquare size={11} className="mt-0.5 shrink-0 text-text-muted" />
              <div className="min-w-0 flex-1">
                <div className="mb-0.5 text-[9.5px] font-semibold uppercase tracking-wider text-text-faint">
                  Said to user
                </div>
                <p className="line-clamp-3 text-[11.5px] leading-relaxed text-text-secondary">
                  {messagePreview}
                </p>
              </div>
            </div>
          )}

          {!step.reasoning &&
            !step.reasoning_streaming &&
            toolCalls.length === 0 &&
            events.length === 0 &&
            !messagePreview && (
              <div className="py-1 text-[11px] italic text-text-faint">
                No detail recorded for this step.
              </div>
            )}
        </div>
      )}
    </div>
  );
}

function EventGroup({ events }: { events: StreamEvent[] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="my-2 overflow-hidden rounded-md border border-border bg-surface-1">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left transition-colors hover:bg-surface-2"
      >
        <ArrowRight size={11} className="shrink-0 text-text-muted" />
        <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-text-muted">
          Side effects
        </span>
        <Badge tone="outline" size="xs" mono className="ml-1">
          {events.length}
        </Badge>
        <span className="ml-auto text-text-muted">
          {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        </span>
      </button>
      {open && (
        <div className="border-t border-border bg-surface-0 px-2.5 py-2">
          <div className="flex flex-col gap-1">
            {events.map((e, i) => (
              <EventLine key={`${e.timestamp}-${i}`} event={e} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function EventLine({ event }: { event: StreamEvent }) {
  switch (event.type) {
    case "command": {
      const c = event as CommandEvent;
      return (
        <div className="flex items-start gap-2 font-mono text-[10.5px]">
          <Terminal size={10} className="mt-0.5 shrink-0 text-accent" />
          <span className="flex-1 truncate text-text-secondary">{c.command}</span>
          <Badge tone={c.exit_code === 0 ? "success" : "danger"} size="xs" mono>
            {c.exit_code}
          </Badge>
        </div>
      );
    }
    case "op": {
      const o = event as OpEvent;
      return (
        <div className="flex items-start gap-2 font-mono text-[10.5px]">
          <Database size={10} className="mt-0.5 shrink-0 text-info" />
          <span className="shrink-0 text-accent">{o.op}</span>
          <span className="flex-1 truncate text-text-secondary">{o.path}</span>
          <span className="shrink-0 text-text-faint">{formatBytes(o.bytes)}</span>
        </div>
      );
    }
    case "mcp_tool_call": {
      const m = event as McpToolCallEvent;
      return (
        <div className="flex items-start gap-2 font-mono text-[10.5px]">
          <Wrench size={10} className="mt-0.5 shrink-0 text-warning" />
          <span className="flex-1 truncate text-text-secondary">{m.tool}</span>
          <span className="shrink-0 text-text-faint">{m.duration_ms}ms</span>
        </div>
      );
    }
    case "mock_request": {
      const r = event as MockRequestEvent;
      return (
        <div className="flex items-start gap-2 font-mono text-[10.5px]">
          <Globe size={10} className="mt-0.5 shrink-0 text-text-muted" />
          <span className="shrink-0 rounded bg-surface-3 px-1 text-text-secondary">{r.method}</span>
          <span className="flex-1 truncate text-text-secondary">{r.path}</span>
          <Badge tone={r.status_code < 400 ? "success" : "danger"} size="xs" mono>
            {r.status_code}
          </Badge>
        </div>
      );
    }
    default:
      return null;
  }
}
