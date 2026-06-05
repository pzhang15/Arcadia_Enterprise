import type { RunStep, ToolCallState } from "@/types/agui";
import type { ReplayAction } from "@/types/replay";
import { intentEffectFlag } from "./replayFold";
import { cn } from "@/lib/utils";

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function shortFp(f: string): string {
  return f.length > 10 ? `${f.slice(0, 8)}…` : f;
}

interface Props {
  step: RunStep;
  toolCalls: ToolCallState[];
  actionsByTc: Map<string, ReplayAction[]>;
  selectedOpIdx: number | null;
  onSelectOp: (idx: number) => void;
}

export default function IntentCommandCard({
  step,
  toolCalls,
  actionsByTc,
  selectedOpIdx,
  onSelectOp,
}: Props) {
  const opCount = toolCalls.reduce(
    (n, tc) => n + (actionsByTc.get(tc.id)?.length ?? 0),
    0,
  );
  const hasFlag = toolCalls.some((tc) =>
    (actionsByTc.get(tc.id) ?? []).some(
      (a) => intentEffectFlag(step.reasoning, a).mismatch,
    ),
  );
  return (
    <div
      className={cn(
        "mx-2 my-2 overflow-hidden rounded-lg border bg-surface-0",
        hasFlag ? "border-warning/45" : "border-border",
      )}
    >
      <div className="flex items-center gap-2 border-b border-border bg-surface-1 px-3 py-1.5 text-[11px]">
        <span
          className={cn(
            "h-1.5 w-1.5 rounded-full",
            step.status === "error"
              ? "bg-danger"
              : step.status === "completed"
                ? "bg-success"
                : "bg-info",
          )}
        />
        <b className="font-medium text-text-primary">{step.name}</b>
        <span className="ml-auto font-mono text-[9px] text-text-muted">
          {toolCalls.length} cmd · {opCount} ops{hasFlag ? " · ⚑" : ""}
        </span>
      </div>

      <div className="px-3 py-2 text-[12px] leading-relaxed text-text-secondary">
        <span className="mr-1.5 font-mono text-[9px] text-text-muted">
          ⓘ self-reported
        </span>
        {step.reasoning ? (
          <span className="underline decoration-text-faint decoration-dotted underline-offset-2">
            {step.reasoning.length > 200
              ? `${step.reasoning.slice(0, 200)}…`
              : step.reasoning}
          </span>
        ) : (
          <span className="italic text-text-faint">
            No stated intent for this step
          </span>
        )}
      </div>

      {toolCalls.map((tc) => {
        const acts = actionsByTc.get(tc.id) ?? [];
        return (
          <div
            key={tc.id}
            className="border-t border-border px-3 py-2 font-mono text-[11px]"
          >
            <div className="flex items-center gap-2 text-text-primary">
              <span className="text-success">$</span>
              <span className="truncate">{tc.args || tc.name}</span>
              <span
                className={cn(
                  "ml-auto shrink-0",
                  tc.exit_code ? "text-danger" : "text-text-muted",
                )}
              >
                exit {tc.exit_code ?? 0}
              </span>
            </div>
            {acts.length === 0 && (
              <div className="ml-4 mt-1 text-[10px] text-text-faint">
                no observed VFS ops
              </div>
            )}
            {acts.map((a) => {
              const flag = intentEffectFlag(step.reasoning, a);
              const sel = a.idx === selectedOpIdx;
              return (
                <div key={a.idx}>
                  <button
                    onClick={() => onSelectOp(a.idx)}
                    className={cn(
                      "mt-1.5 block w-full rounded-r border-l-2 px-2 py-1 text-left text-[10.5px]",
                      sel
                        ? "border-accent bg-accent-soft text-text-primary"
                        : "border-captured bg-captured/5 text-text-secondary hover:bg-surface-2",
                    )}
                  >
                    └ <b className="text-text-secondary">{a.op}</b>{" "}
                    <span className="text-text-primary">{a.path}</span> ·{" "}
                    {a.source} · {fmtBytes(a.bytes)}
                    {a.revision ? ` · rev ${a.revision}` : ""}
                    {a.fingerprint ? ` · ${shortFp(a.fingerprint)}` : ""}
                    {a.is_cache && (
                      <span className="ml-1 rounded bg-surface-2 px-1 text-text-muted">
                        cache
                      </span>
                    )}
                  </button>
                  {flag.mismatch && (
                    <div className="mt-1.5 flex items-center gap-2 rounded-md border border-warning/45 bg-warning-soft px-2 py-1 text-[10.5px] text-warning">
                      ⚑ INTENT≠EFFECT — {flag.reason}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        );
      })}
    </div>
  );
}
