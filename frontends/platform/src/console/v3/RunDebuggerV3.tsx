import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useAgentStream } from "@/hooks/useAgentStream";
import { getReplay } from "@/api/client";
import type { ReplayResponse, ReplayState } from "@/types/replay";
import type { ToolCallState } from "@/types/agui";
import { foldReplay, groupActionsByToolCall } from "./replayFold";
import IntentCommandCard from "./IntentCommandCard";

function fmtBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

function DiffPanel({ fold }: { fold: ReplayState }) {
  const op = fold.cursor_op;
  if (!op) return null;
  const isWrite = fold.diff?.kind === "write";
  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-hidden rounded-lg border border-border bg-surface-0">
        <div className="flex items-center gap-2 border-b border-border bg-surface-1 px-3 py-2 text-[11px]">
          <span
            className={`rounded px-1.5 py-0.5 font-mono text-[9px] ${
              isWrite
                ? "bg-captured-soft text-captured"
                : "bg-info-soft text-info"
            }`}
          >
            {op.op.toUpperCase()}
          </span>
          <b className="font-mono text-text-primary">
            idx {op.idx} · {op.path}
          </b>
        </div>
        <dl className="grid grid-cols-[110px_1fr] gap-x-3 gap-y-1.5 p-3 font-mono text-[11px]">
          <dt className="text-text-muted">source</dt>
          <dd className="text-text-primary">{op.source}</dd>
          <dt className="text-text-muted">bytes · dur</dt>
          <dd className="text-text-primary">
            {op.bytes.toLocaleString()} B · {op.duration_ms} ms
          </dd>
          <dt className="text-text-muted">cache</dt>
          <dd className="text-text-secondary">
            {op.is_cache ? "served from cache " : "fetched "}
            <span className="rounded bg-surface-2 px-1 text-[9px] text-text-muted">
              derived · is_cache
            </span>
          </dd>
          <dt className="text-text-muted">fingerprint</dt>
          <dd className={op.fingerprint ? "text-text-primary" : "text-text-faint"}>
            {op.fingerprint ?? "— (source has no ETag)"}
          </dd>
          <dt className="text-text-muted">revision</dt>
          <dd className={op.revision ? "text-text-primary" : "text-text-faint"}>
            {op.revision ?? "—"}
          </dd>
          <dt className="text-text-muted">tool_call</dt>
          <dd className="text-text-secondary">{op.tool_call_id ?? "—"}</dd>
        </dl>
      </div>
      <div className="rounded-lg border border-border bg-surface-0 p-3 text-[11px]">
        <div className="mb-2 font-medium text-text-secondary">
          State folded at this cursor
        </div>
        <div className="font-mono text-[10.5px] text-text-muted">
          overlay: {fold.overlay.length} write
          {fold.overlay.length === 1 ? "" : "s"}
          {fold.overlay.length > 0 &&
            ` (${fold.overlay.map((o) => o.path).join(", ")})`}
          <br />
          reads-so-far: {fold.reads_count} path
          {fold.reads_count === 1 ? "" : "s"}
        </div>
      </div>
    </div>
  );
}

export default function RunDebuggerV3() {
  const { sessionId = "" } = useParams();
  const nav = useNavigate();
  const stream = useAgentStream(sessionId);
  const [replay, setReplay] = useState<ReplayResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [cursor, setCursor] = useState(-1);

  useEffect(() => {
    if (!sessionId) return;
    let live = true;
    setErr(null);
    getReplay(sessionId)
      .then((r) => {
        if (!live) return;
        setReplay(r);
        setCursor(r.total - 1);
      })
      .catch((e) => live && setErr(String((e as Error)?.message ?? e)));
    return () => {
      live = false;
    };
  }, [sessionId]);

  const actions = useMemo(() => replay?.actions ?? [], [replay]);
  const actionsByTc = useMemo(
    () => groupActionsByToolCall(actions),
    [actions],
  );
  const fold = useMemo(() => foldReplay(actions, cursor), [actions, cursor]);
  const steps = useMemo(
    () =>
      Object.values(stream.steps).sort((a, b) => a.started_at - b.started_at),
    [stream.steps],
  );
  const selectedOpIdx =
    cursor >= 0 && cursor < actions.length ? actions[cursor].idx : null;

  return (
    <div className="flex h-full flex-col text-text-primary">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2 text-[12px]">
        <button
          onClick={() => nav("/v3")}
          className="flex items-center gap-1 rounded px-2 py-1 text-text-muted hover:bg-surface-2 hover:text-text-primary"
        >
          <ArrowLeft size={13} /> Runs
        </button>
        <span className="font-mono text-text-secondary">
          / <b className="text-text-primary">{sessionId}</b> / Time-Travel
        </span>
        <span className="ml-auto font-mono text-[11px] text-text-muted">
          {replay ? `${replay.total} ops · ${steps.length} steps` : ""}
        </span>
      </div>
      <div className="flex min-h-0 flex-1">
        <div className="w-[420px] shrink-0 overflow-auto border-r border-border bg-surface-0">
          {steps.length === 0 && (
            <div className="p-4 text-[12px] text-text-muted">
              No reasoning/commands reconstructed for this session yet.
            </div>
          )}
          {steps.map((step) => {
            const tcs = step.tool_call_ids
              .map((id) => stream.toolCalls[id])
              .filter(Boolean) as ToolCallState[];
            return (
              <IntentCommandCard
                key={step.id}
                step={step}
                toolCalls={tcs}
                actionsByTc={actionsByTc}
                selectedOpIdx={selectedOpIdx}
                onSelectOp={(idx) =>
                  setCursor(actions.findIndex((a) => a.idx === idx))
                }
              />
            );
          })}
        </div>

        <div className="flex min-w-0 flex-1 flex-col">
          <div className="flex h-9 items-center gap-3 border-b border-border px-3 text-[12px]">
            <span className="flex h-9 items-center border-b-2 border-accent font-medium text-text-primary">
              Diff
            </span>
            <span className="ml-auto rounded bg-captured-soft px-2 py-0.5 font-mono text-[9px] text-captured">
              EXACT · /replay
            </span>
          </div>
          <div className="min-h-0 flex-1 overflow-auto p-4">
            {err && (
              <div className="rounded-lg border border-border bg-surface-1 p-3 text-[12px] text-text-muted">
                <div className="mb-1 font-medium text-text-secondary">
                  Replay unavailable for this session
                </div>
                The intent+command trace on the left comes from{" "}
                <span className="font-mono text-text-secondary">
                  getSessionTrace
                </span>
                . The Diff/state fold needs the{" "}
                <span className="font-mono text-text-secondary">
                  /api/sessions/:id/replay
                </span>{" "}
                endpoint (added in this slice) on the running backend, plus a
                run that recorded VFS ops.
                <div className="mt-1.5 font-mono text-[10px] text-text-faint">
                  {err}
                </div>
              </div>
            )}
            {!err && fold.cursor_op && <DiffPanel fold={fold} />}
            {!err && !fold.cursor_op && (
              <div className="text-[12px] text-text-muted">
                {actions.length === 0
                  ? "This session recorded no VFS ops (the agent ran no commands, or needs OPENAI_API_KEY)."
                  : "No data-plane op at this cursor."}
              </div>
            )}
          </div>
          {actions.length > 0 && (
            <div className="flex h-10 items-center gap-3 border-t border-border px-3">
              <input
                type="range"
                min={0}
                max={actions.length - 1}
                value={cursor < 0 ? 0 : cursor}
                onChange={(e) => setCursor(Number(e.target.value))}
                className="flex-1 accent-accent"
              />
              <span className="shrink-0 font-mono text-[10px] text-text-secondary">
                #{cursor + 1} of {actions.length}
                {fold.cursor_op ? ` · idx ${fold.cursor_op.idx}` : ""}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
