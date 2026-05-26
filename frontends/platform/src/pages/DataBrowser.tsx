import { useEffect, useState } from "react";
import {
  fetchTickets,
  fetchExpenses,
  fetchIncidents,
  fetchAccounts,
  fetchContracts,
  fetchAudits,
} from "@/api/client";

interface MountEntry {
  id: string;
  label: string;
  colorClass: string;
  fetchFn: () => Promise<Record<string, unknown>[]>;
}

function toRecords<T extends object>(fn: () => Promise<T[]>): () => Promise<Record<string, unknown>[]> {
  return () => fn().then((items) => items as unknown as Record<string, unknown>[]);
}

const MOUNTS: MountEntry[] = [
  {
    id: "tickets",
    label: "IT Helpdesk",
    colorClass: "bg-mount-tickets",
    fetchFn: toRecords(() => fetchTickets("it-helpdesk")),
  },
  {
    id: "finance",
    label: "Finance",
    colorClass: "bg-mount-finance",
    fetchFn: toRecords(fetchExpenses),
  },
  {
    id: "pagerduty",
    label: "Incidents",
    colorClass: "bg-mount-pagerduty",
    fetchFn: toRecords(fetchIncidents),
  },
  {
    id: "customers",
    label: "Customers",
    colorClass: "bg-mount-customers",
    fetchFn: toRecords(fetchAccounts),
  },
  {
    id: "compliance",
    label: "Compliance",
    colorClass: "bg-mount-compliance",
    fetchFn: toRecords(fetchContracts),
  },
  {
    id: "audits",
    label: "Audits",
    colorClass: "bg-mount-compliance",
    fetchFn: toRecords(fetchAudits),
  },
];

export default function DataBrowser() {
  const [selectedMount, setSelectedMount] = useState(MOUNTS[0].id);
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const mount = MOUNTS.find((m) => m.id === selectedMount) ?? MOUNTS[0];

  useEffect(() => {
    setLoading(true);
    setError(null);
    setExpandedRow(null);
    mount
      .fetchFn()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [mount]);

  const columns = data.length > 0 ? Object.keys(data[0]).filter((k) => typeof data[0][k] !== "object") : [];

  return (
    <div className="flex h-full">
      <div className="flex w-[200px] shrink-0 flex-col border-r border-border bg-surface-1">
        <div className="border-b border-border px-4 py-3">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
            Data Sources
          </h2>
        </div>
        <div className="flex-1 overflow-y-auto py-1">
          {MOUNTS.map((m) => (
            <button
              key={m.id}
              onClick={() => setSelectedMount(m.id)}
              className={`flex w-full items-center gap-2.5 px-4 py-2 text-left text-[13px] transition-colors ${
                selectedMount === m.id
                  ? "bg-accent-muted text-accent"
                  : "text-text-secondary hover:bg-surface-3 hover:text-text-primary"
              }`}
            >
              <span className={`h-2 w-2 shrink-0 rounded-full ${m.colorClass}`} />
              <span className="truncate">{m.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="flex items-center gap-3 border-b border-border px-6 py-3">
          <span className={`h-2.5 w-2.5 rounded-full ${mount.colorClass}`} />
          <h1 className="text-sm font-semibold text-text-primary">
            {mount.label}
          </h1>
          <span className="font-mono text-xs text-text-muted">
            {data.length} records
          </span>
        </div>

        <div className="flex-1 overflow-auto">
          {loading && (
            <div className="flex items-center justify-center py-20">
              <span className="animate-pulse-fade text-sm text-text-muted">
                Loading...
              </span>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center gap-2 py-20">
              <span className="text-sm text-danger">Failed to load data</span>
              <span className="text-xs text-text-muted">{error}</span>
            </div>
          )}

          {!loading && !error && data.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-2 py-20">
              <span className="text-3xl opacity-30">&#x1F4C2;</span>
              <span className="text-sm text-text-muted">
                No records found. Run seed data generation first.
              </span>
            </div>
          )}

          {!loading && !error && data.length > 0 && (
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr>
                  {columns.map((col) => (
                    <th
                      key={col}
                      className="sticky top-0 z-10 border-b border-border bg-surface-1 px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-wider text-text-muted"
                    >
                      {col.replace(/_/g, " ")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.map((row, idx) => (
                  <tr
                    key={idx}
                    onClick={() =>
                      setExpandedRow(expandedRow === idx ? null : idx)
                    }
                    className="cursor-pointer border-b border-border transition-colors hover:bg-surface-2"
                  >
                    {columns.map((col) => (
                      <td
                        key={col}
                        className="max-w-[200px] truncate px-4 py-2 font-mono text-xs text-text-secondary"
                      >
                        {String(row[col] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
