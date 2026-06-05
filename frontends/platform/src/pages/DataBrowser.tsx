import { Fragment, useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  ChevronDown,
  ChevronRight,
  ClipboardCheck,
  Database,
  FileText,
  Search,
  TicketCheck,
  Users,
  Wallet,
  Zap,
} from "lucide-react";
import {
  fetchTickets,
  fetchExpenses,
  fetchIncidents,
  fetchAccounts,
  fetchContracts,
  fetchAudits,
} from "@/api/client";
import { cn } from "@/lib/utils";
import { Badge, EmptyState, SectionLabel } from "@/components/ui";

interface MountEntry {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  fetchFn: () => Promise<Record<string, unknown>[]>;
  columns?: string[];
}

function toRecords<T extends object>(
  fn: () => Promise<T[]>,
): () => Promise<Record<string, unknown>[]> {
  return () =>
    fn().then((items) => items as unknown as Record<string, unknown>[]);
}

const MOUNTS: MountEntry[] = [
  {
    id: "tickets",
    label: "IT Helpdesk",
    description: "Tickets & service requests",
    icon: <TicketCheck size={14} />,
    color: "text-mount-tickets",
    fetchFn: toRecords(() => fetchTickets("it-helpdesk")),
    columns: ["ticket_id", "subject", "queue", "status", "priority", "created_at"],
  },
  {
    id: "finance",
    label: "Finance",
    description: "Expenses & purchase orders",
    icon: <Wallet size={14} />,
    color: "text-mount-finance",
    fetchFn: toRecords(fetchExpenses),
    columns: [
      "expense_id",
      "submitter",
      "amount",
      "category",
      "status",
      "department",
    ],
  },
  {
    id: "pagerduty",
    label: "Incidents",
    description: "PagerDuty incidents",
    icon: <Zap size={14} />,
    color: "text-mount-pagerduty",
    fetchFn: toRecords(fetchIncidents),
    columns: ["id", "title", "status", "severity", "service", "created_at"],
  },
  {
    id: "customers",
    label: "Customers",
    description: "Accounts & ARR",
    icon: <Users size={14} />,
    color: "text-mount-customers",
    fetchFn: toRecords(fetchAccounts),
    columns: [
      "account_id",
      "company_name",
      "tier",
      "arr",
      "health_score",
      "csm",
    ],
  },
  {
    id: "compliance",
    label: "Compliance",
    description: "Contracts & policies",
    icon: <ClipboardCheck size={14} />,
    color: "text-mount-compliance",
    fetchFn: toRecords(fetchContracts),
    columns: ["contract_id", "counterparty", "type", "status", "owner", "end_date"],
  },
  {
    id: "audits",
    label: "Audits",
    description: "SOC2 / ISO frameworks",
    icon: <FileText size={14} />,
    color: "text-mount-compliance",
    fetchFn: toRecords(fetchAudits),
    columns: ["audit_id", "framework", "status", "due_date", "checklist"],
  },
];

const MONO_COLUMNS = new Set([
  "id",
  "ticket_id",
  "expense_id",
  "account_id",
  "contract_id",
  "audit_id",
  "queue",
  "service",
]);

const STATUS_TONE: Record<
  string,
  "success" | "warning" | "danger" | "info" | "neutral"
> = {
  open: "info",
  active: "info",
  in_progress: "warning",
  pending: "warning",
  approved: "success",
  resolved: "success",
  closed: "neutral",
  failed: "danger",
  rejected: "danger",
  expired: "danger",
  critical: "danger",
  high: "warning",
  medium: "info",
  low: "neutral",
};

function statusTone(value: string) {
  const key = value.toLowerCase().replace(/\s+/g, "_");
  return STATUS_TONE[key] || "neutral";
}

function formatCell(col: string, value: unknown): React.ReactNode {
  if (value === null || value === undefined)
    return <span className="text-text-faint">—</span>;
  if (
    (col === "status" || col === "priority" || col === "severity" || col === "tier") &&
    typeof value === "string"
  ) {
    return (
      <Badge tone={statusTone(value)} size="xs">
        {value}
      </Badge>
    );
  }
  if (col === "amount" || col === "arr") {
    if (typeof value === "number") {
      return (
        <span className="font-mono tabular-nums">
          ${Intl.NumberFormat("en-US").format(value)}
        </span>
      );
    }
  }
  if (col === "health_score" && typeof value === "number") {
    const tone =
      value >= 80 ? "success" : value >= 50 ? "warning" : "danger";
    return (
      <Badge tone={tone} size="xs" mono>
        {value}
      </Badge>
    );
  }
  if (typeof value === "number")
    return (
      <span className="font-mono tabular-nums">
        {Intl.NumberFormat("en-US").format(value)}
      </span>
    );
  if (Array.isArray(value))
    return (
      <span className="text-text-muted">
        {value.length} item{value.length === 1 ? "" : "s"}
      </span>
    );
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (typeof record.name === "string") return record.name;
    if (typeof record.email === "string") return record.email;
    return (
      <span className="text-text-muted">{JSON.stringify(value).slice(0, 50)}</span>
    );
  }
  return String(value);
}

function pickColumns(
  data: Record<string, unknown>[],
  preferred: string[] | undefined,
): string[] {
  if (data.length === 0) return [];
  const keys = Object.keys(data[0]);
  if (!preferred) return keys.slice(0, 6);
  const selected = preferred.filter((k) => keys.includes(k));
  return selected.length > 0 ? selected : keys.slice(0, 6);
}

export default function DataBrowser() {
  const [selectedMount, setSelectedMount] = useState(MOUNTS[0].id);
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);
  const [search, setSearch] = useState("");

  const mount = MOUNTS.find((m) => m.id === selectedMount) ?? MOUNTS[0];

  useEffect(() => {
    setLoading(true);
    setError(null);
    setExpandedRow(null);
    setSearch("");
    mount
      .fetchFn()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [mount]);

  const columns = useMemo(
    () => pickColumns(data, mount.columns),
    [data, mount.columns],
  );

  const filtered = useMemo(() => {
    if (!search) return data;
    const q = search.toLowerCase();
    return data.filter((row) =>
      Object.values(row).some((v) =>
        String(v ?? "")
          .toLowerCase()
          .includes(q),
      ),
    );
  }, [data, search]);

  return (
    <div className="flex h-full overflow-hidden">
      <div className="flex w-[260px] shrink-0 flex-col border-r border-border bg-surface-1/40">
        <div className="border-b border-border px-4 py-4">
          <div className="mb-1 flex items-center gap-2">
            <Database size={14} className="text-text-muted" />
            <SectionLabel>Data Sources</SectionLabel>
          </div>
          <p className="text-[11px] text-text-faint">
            Mounted via Arcadia VFS
          </p>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {MOUNTS.map((m) => {
            const selected = selectedMount === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setSelectedMount(m.id)}
                className={cn(
                  "group mb-0.5 flex w-full items-start gap-2.5 rounded-lg border px-2.5 py-2.5 text-left transition-all duration-150",
                  selected
                    ? "border-accent/30 bg-accent-soft"
                    : "border-transparent hover:border-border hover:bg-surface-2",
                )}
              >
                <span
                  className={cn(
                    "mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md border border-border bg-surface-1",
                    m.color,
                    selected && "border-accent/30",
                  )}
                >
                  {m.icon}
                </span>
                <div className="min-w-0 flex-1 leading-tight">
                  <div
                    className={cn(
                      "truncate text-[13px] font-medium",
                      selected ? "text-accent" : "text-text-primary",
                    )}
                  >
                    {m.label}
                  </div>
                  <div className="mt-0.5 truncate text-[11px] text-text-muted">
                    {m.description}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface-1/60 px-6 backdrop-blur-md">
          <span
            className={cn(
              "grid h-8 w-8 place-items-center rounded-lg border border-border bg-surface-2",
              mount.color,
            )}
          >
            {mount.icon}
          </span>
          <div>
            <h1 className="text-[14px] font-semibold tracking-tight text-text-primary">
              {mount.label}
            </h1>
            <p className="text-[11px] text-text-muted">{mount.description}</p>
          </div>
          <Badge tone="outline" size="sm" mono className="ml-1">
            {data.length} records
          </Badge>
          <div className="ml-auto flex items-center gap-2">
            <div className="relative">
              <Search
                size={13}
                className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted"
              />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Filter records..."
                className="h-9 w-64 rounded-lg border border-border bg-surface-2 pl-8 pr-3 text-[12px] text-text-primary placeholder:text-text-muted focus:border-accent"
              />
            </div>
          </div>
        </header>

        <div className="flex-1 overflow-auto">
          {loading && (
            <div className="flex items-center justify-center py-24">
              <div className="flex items-center gap-3 text-text-muted">
                <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" />
                <span className="text-[13px]">Loading records…</span>
              </div>
            </div>
          )}

          {error && (
            <EmptyState
              icon={<AlertCircle size={22} />}
              title="Failed to load records"
              description={error}
              size="lg"
            />
          )}

          {!loading && !error && data.length === 0 && (
            <EmptyState
              icon={<Database size={22} />}
              title="No records found"
              description="Run the seed data generator to populate this data source, then refresh."
              size="lg"
            />
          )}

          {!loading && !error && data.length > 0 && (
            <table className="min-w-full border-collapse text-[13px]">
              <thead>
                <tr>
                  <th className="sticky top-0 z-10 w-8 border-b border-border bg-surface-1/95 px-4 py-2.5 backdrop-blur" />
                  {columns.map((col) => (
                    <th
                      key={col}
                      className="sticky top-0 z-10 whitespace-nowrap border-b border-border bg-surface-1/95 px-4 py-2.5 text-left text-[10px] font-semibold uppercase tracking-[0.08em] text-text-muted backdrop-blur"
                    >
                      {col.replace(/_/g, " ")}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((row, idx) => (
                  <Fragment key={idx}>
                    <tr
                      onClick={() =>
                        setExpandedRow(expandedRow === idx ? null : idx)
                      }
                      className={cn(
                        "cursor-pointer border-b border-border transition-colors hover:bg-surface-2/60",
                        expandedRow === idx && "bg-surface-2/80",
                      )}
                    >
                      <td className="px-4 py-2.5 align-middle text-text-faint">
                        {expandedRow === idx ? (
                          <ChevronDown size={13} />
                        ) : (
                          <ChevronRight size={13} />
                        )}
                      </td>
                      {columns.map((col) => (
                        <td
                          key={col}
                          className={cn(
                            "max-w-[260px] truncate px-4 py-2.5 align-middle",
                            MONO_COLUMNS.has(col)
                              ? "font-mono text-[11.5px] text-text-secondary"
                              : "text-[13px] text-text-secondary",
                          )}
                        >
                          {formatCell(col, row[col])}
                        </td>
                      ))}
                    </tr>
                    {expandedRow === idx && (
                      <tr className="border-b border-border bg-surface-0">
                        <td
                          colSpan={columns.length + 1}
                          className="px-4 py-4"
                        >
                          <div className="rounded-lg border border-border bg-surface-1 p-4">
                            <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                              Full record
                            </div>
                            <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[11.5px] leading-relaxed text-text-secondary">
                              {JSON.stringify(row, null, 2)}
                            </pre>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
