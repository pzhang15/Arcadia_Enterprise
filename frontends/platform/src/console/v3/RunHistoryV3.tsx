import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listSessions } from "@/api/client";
import { selectActiveDetail, useConsoleStore } from "@/lib/consoleStore";
import { cn } from "@/lib/utils";

interface SessionRow {
  id: string;
  status: string;
  services: string[];
  created_at: number;
  message_count: number;
  last_message: string;
}

function rel(ts: number): string {
  const s = Date.now() / 1000 - ts;
  if (s < 60) return `${Math.max(0, Math.floor(s))}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export default function RunHistoryV3() {
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();
  const ws = selectActiveDetail(useConsoleStore());

  useEffect(() => {
    listSessions()
      .then((s) => setSessions(s as SessionRow[]))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex h-full flex-col text-text-primary">
      <div className="flex items-center gap-3 border-b border-border px-5 py-3">
        <h1 className="text-[15px] font-semibold tracking-tight">Runs</h1>
        <span className="text-[12px] text-text-muted">
          {loading ? "loading…" : `${sessions.length} sessions`}
          {ws ? ` · ${ws.name} · ${ws.branch}` : ""}
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full text-[12px]">
          <thead className="sticky top-0 bg-surface-0">
            <tr className="text-[9px] uppercase tracking-wide text-text-muted">
              <th className="px-3 py-2 text-left"></th>
              <th className="px-3 py-2 text-left">Session</th>
              <th className="px-3 py-2 text-left">Intent preview</th>
              <th className="px-3 py-2 text-left">Services</th>
              <th className="px-3 py-2 text-left">Msgs</th>
              <th className="px-3 py-2 text-left">Started</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr
                key={s.id}
                onClick={() => nav(`/v3/runs/${s.id}`)}
                className="cursor-pointer border-b border-border/50 hover:bg-surface-2"
              >
                <td className="px-3 py-2">
                  <span
                    className={cn(
                      "inline-block h-2 w-2 rounded-full",
                      s.status === "error"
                        ? "bg-danger"
                        : s.status === "running"
                          ? "bg-simulated"
                          : "bg-success",
                    )}
                  />
                </td>
                <td className="px-3 py-2 font-mono text-text-primary">{s.id}</td>
                <td className="max-w-[440px] truncate px-3 py-2 text-text-muted">
                  {s.last_message || (
                    <span className="italic text-text-faint">—</span>
                  )}
                </td>
                <td className="px-3 py-2 font-mono text-[10px] text-text-muted">
                  {(s.services || []).join(" · ") || "—"}
                </td>
                <td className="px-3 py-2 font-mono">{s.message_count}</td>
                <td className="px-3 py-2 text-text-muted">{rel(s.created_at)}</td>
              </tr>
            ))}
            {!loading && sessions.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-3 py-12 text-center text-[12px] text-text-muted"
                >
                  No runs yet — start one in the console (or set
                  <span className="mx-1 font-mono text-text-secondary">
                    OPENAI_API_KEY
                  </span>
                  and chat at an agent), then it appears here.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
