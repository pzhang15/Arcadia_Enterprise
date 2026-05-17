interface SessionEntry {
  id: string;
  status: string;
  services: string[];
  created_at: number;
  message_count: number;
  last_message: string;
}

interface Props {
  sessions: SessionEntry[];
  activeId: string | null;
  onSelect: (id: string) => void;
}

function timeAgo(ts: number): string {
  const diff = (Date.now() / 1000 - ts) | 0;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${(diff / 60) | 0}m ago`;
  if (diff < 86400) return `${(diff / 3600) | 0}h ago`;
  return `${(diff / 86400) | 0}d ago`;
}

export default function SessionHistory({
  sessions,
  activeId,
  onSelect,
}: Props) {
  if (sessions.length === 0) {
    return (
      <div className="text-sm text-tertiary" style={{ padding: "8px 0" }}>
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
            padding: "8px 10px",
            borderRadius: "var(--radius-sm)",
            cursor: "pointer",
            background:
              s.id === activeId ? "var(--bg-hover)" : "transparent",
            borderLeft:
              s.id === activeId
                ? "2px solid var(--accent)"
                : "2px solid transparent",
            transition: "all 0.1s",
          }}
        >
          <div
            style={{
              fontSize: 12,
              color: "var(--text-primary)",
              marginBottom: 2,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {s.last_message || `Session ${s.id}`}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-tertiary">
              {s.message_count} msgs
            </span>
            <span className="text-sm text-tertiary">
              {timeAgo(s.created_at)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
