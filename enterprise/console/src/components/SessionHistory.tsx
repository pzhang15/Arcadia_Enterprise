interface SessionEntry {
  id: string;
  status: string;
  task: string;
  created_at: number;
  completed_at: number | null;
}

interface Props {
  sessions: SessionEntry[];
  activeId: string | null;
  onSelect: (id: string) => void;
}

function timeAgo(ts: number): string {
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function statusBadge(status: string) {
  const map: Record<string, string> = {
    created: "neutral",
    running: "info",
    completed: "success",
    error: "danger",
  };
  return <span className={`badge ${map[status] || "neutral"}`}>{status}</span>;
}

export default function SessionHistory({ sessions, activeId, onSelect }: Props) {
  if (sessions.length === 0) {
    return (
      <div
        style={{
          padding: "20px 0",
          textAlign: "center",
          color: "var(--text-tertiary)",
          fontSize: 12,
        }}
      >
        No sessions yet
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {sessions.map((s) => (
        <div
          key={s.id}
          onClick={() => onSelect(s.id)}
          style={{
            padding: "10px 12px",
            borderRadius: "var(--radius-sm)",
            cursor: "pointer",
            background: s.id === activeId ? "var(--bg-hover)" : "transparent",
            borderLeft:
              s.id === activeId
                ? "2px solid var(--accent)"
                : "2px solid transparent",
            transition: "all 0.15s",
          }}
        >
          <div
            className="truncate"
            style={{ fontSize: 12, marginBottom: 4, color: "var(--text-primary)" }}
          >
            {s.task || "New session"}
          </div>
          <div className="flex items-center gap-2">
            {statusBadge(s.status)}
            <span className="text-sm text-tertiary">{timeAgo(s.created_at)}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
