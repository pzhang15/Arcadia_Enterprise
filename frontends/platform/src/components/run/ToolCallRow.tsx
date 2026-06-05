import { useState } from "react";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleX,
  Loader2,
  Wrench,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui";
import type { ToolCallState } from "@/types/agui";

interface Props {
  tc: ToolCallState;
}

function durationMs(tc: ToolCallState): string {
  if (!tc.ended_at) return tc.status === "running" ? "—" : "—";
  const ms = tc.ended_at - tc.started_at;
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

function tryFormatJson(text: string | undefined): string {
  if (!text) return "";
  const trimmed = text.trim();
  if (!trimmed.startsWith("{") && !trimmed.startsWith("[")) return text;
  try {
    return JSON.stringify(JSON.parse(trimmed), null, 2);
  } catch {
    return text;
  }
}

export function ToolCallRow({ tc }: Props) {
  const [open, setOpen] = useState(false);
  const StatusIcon =
    tc.status === "running"
      ? Loader2
      : tc.status === "error"
        ? CircleX
        : CheckCircle2;
  const statusColor =
    tc.status === "running"
      ? "text-info"
      : tc.status === "error"
        ? "text-danger"
        : "text-success";

  return (
    <div className="overflow-hidden rounded-md border border-border bg-surface-1">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-2.5 py-1.5 text-left transition-colors hover:bg-surface-2"
      >
        <StatusIcon
          size={12}
          className={cn(
            "shrink-0",
            statusColor,
            tc.status === "running" && "animate-spin",
          )}
        />
        <Wrench size={11} className="shrink-0 text-text-muted" />
        <span className="flex-1 truncate font-mono text-[11.5px] text-text-secondary">
          {tc.name}
        </span>
        {tc.exit_code !== undefined && (
          <Badge tone={tc.exit_code === 0 ? "success" : "danger"} size="xs" mono>
            exit {tc.exit_code}
          </Badge>
        )}
        <span className="shrink-0 font-mono text-[10px] text-text-faint">
          {durationMs(tc)}
        </span>
        <span className="shrink-0 text-text-muted">
          {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
        </span>
      </button>
      {open && (tc.args || tc.result) && (
        <div className="grid gap-1.5 border-t border-border bg-surface-0 px-2.5 py-2">
          {tc.args && (
            <div>
              <div className="mb-0.5 text-[9.5px] font-semibold uppercase tracking-wider text-text-faint">
                Arguments
              </div>
              <pre className="max-h-32 overflow-auto whitespace-pre-wrap font-mono text-[10.5px] leading-relaxed text-text-secondary">
                {tryFormatJson(tc.args)}
              </pre>
            </div>
          )}
          {tc.result && (
            <div>
              <div className="mb-0.5 text-[9.5px] font-semibold uppercase tracking-wider text-text-faint">
                Result
              </div>
              <pre className="max-h-40 overflow-auto whitespace-pre-wrap font-mono text-[10.5px] leading-relaxed text-text-secondary">
                {tryFormatJson(tc.result)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
