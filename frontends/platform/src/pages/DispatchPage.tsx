import { useCallback, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Bell,
  Briefcase,
  Calendar,
  Check,
  ChevronLeft,
  Headphones,
  Layers,
  Send,
  Shield,
  ShieldCheck,
  Sliders,
  TicketCheck,
  User,
  Zap,
} from "lucide-react";
import { createSession } from "@/api/client";
import { cn } from "@/lib/utils";
import { Badge, SectionLabel } from "@/components/ui";
import {
  WORKSPACE_TEMPLATES,
  type WorkspaceTemplate,
  findTemplate,
} from "@/lib/workspaceTemplates";
import { upsertInvestigation } from "@/lib/investigationStore";
import {
  SEVERITY_DESCRIPTIONS,
  SEVERITY_ORDER,
  type InvestigationAuthority,
  type InvestigationSeverity,
  type InvestigationTrigger,
} from "@/types/investigation";

const TEMPLATE_ICONS: Record<string, React.ReactNode> = {
  zap: <Zap size={16} />,
  headphones: <Headphones size={16} />,
  "shield-check": <ShieldCheck size={16} />,
  "ticket-check": <TicketCheck size={16} />,
  layers: <Layers size={16} />,
  sliders: <Sliders size={16} />,
  briefcase: <Briefcase size={16} />,
};

const TRIGGER_OPTIONS: { id: InvestigationTrigger; label: string; icon: React.ReactNode }[] = [
  { id: "manual", label: "Manual", icon: <User size={12} /> },
  { id: "alert", label: "Alert", icon: <Bell size={12} /> },
  { id: "ticket", label: "Ticket", icon: <TicketCheck size={12} /> },
  { id: "customer", label: "Customer", icon: <Headphones size={12} /> },
  { id: "scheduled", label: "Scheduled", icon: <Calendar size={12} /> },
  { id: "compliance", label: "Compliance", icon: <Shield size={12} /> },
];

const AUTHORITY_OPTIONS: {
  id: InvestigationAuthority;
  label: string;
  description: string;
}[] = [
  {
    id: "read_only",
    label: "Read-only",
    description: "Agent may read all mounts but never writes.",
  },
  {
    id: "approve_writes",
    label: "Approve writes",
    description: "Agent can propose writes; humans approve before commit.",
  },
  {
    id: "autonomous",
    label: "Autonomous",
    description: "Agent writes and remediates without further approval.",
  },
];

export default function DispatchPage() {
  const navigate = useNavigate();

  const [templateId, setTemplateId] = useState<string>(WORKSPACE_TEMPLATES[0].id);
  const template = useMemo(() => findTemplate(templateId), [templateId]);
  const [title, setTitle] = useState("");
  const [brief, setBrief] = useState("");
  const [severity, setSeverity] = useState<InvestigationSeverity>(
    template.defaultSeverity,
  );
  const [trigger, setTrigger] = useState<InvestigationTrigger>(
    template.defaultTrigger,
  );
  const [triggerRef, setTriggerRef] = useState("");
  const [authority, setAuthority] = useState<InvestigationAuthority>(
    template.defaultAuthority,
  );
  const [mounts, setMounts] = useState<string[]>(
    template.mounts.map((m) => m.path),
  );
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onPickTemplate = useCallback((t: WorkspaceTemplate) => {
    setTemplateId(t.id);
    setSeverity(t.defaultSeverity);
    setTrigger(t.defaultTrigger);
    setAuthority(t.defaultAuthority);
    setMounts(t.mounts.map((m) => m.path));
  }, []);

  const toggleMount = useCallback((path: string) => {
    setMounts((prev) =>
      prev.includes(path) ? prev.filter((p) => p !== path) : [...prev, path],
    );
  }, []);

  const canSubmit = !!brief.trim() && !submitting;

  const handleDispatch = useCallback(async () => {
    if (!canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const services = Array.from(new Set(template.services));
      const session = await createSession(services);
      upsertInvestigation({
        sessionId: session.id,
        title: title.trim() || brief.trim().slice(0, 80),
        brief: brief.trim(),
        templateId: template.id,
        severity,
        trigger,
        triggerRef: triggerRef.trim() || undefined,
        authority,
        status: "running",
      });
      navigate(`/investigations/${session.id}?autostart=1&brief=${encodeURIComponent(brief.trim())}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to dispatch");
      setSubmitting(false);
    }
  }, [
    canSubmit,
    template,
    title,
    brief,
    severity,
    trigger,
    triggerRef,
    authority,
    navigate,
  ]);

  return (
    <div className="flex h-full w-full flex-col overflow-hidden">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface-1/60 px-6 backdrop-blur-md">
        <button
          onClick={() => navigate(-1)}
          className="grid h-8 w-8 place-items-center rounded-md text-text-muted transition-colors hover:bg-surface-2 hover:text-text-primary"
          title="Back"
        >
          <ChevronLeft size={15} />
        </button>
        <div>
          <h1 className="text-[14px] font-semibold tracking-tight text-text-primary">
            Dispatch agent
          </h1>
          <p className="text-[11px] text-text-muted">
            Configure a Mirage workspace and hand the agent a brief
          </p>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_360px] overflow-hidden">
        <div className="min-w-0 overflow-y-auto">
          <div className="mx-auto max-w-3xl px-6 py-6">
            <section className="mb-7">
              <SectionLabel className="mb-2">1 · Workspace template</SectionLabel>
              <p className="mb-3 text-[12px] text-text-muted">
                Templates pre-configure the Mirage mounts, tool grants, and budget caps
                so the agent only sees what it needs.
              </p>
              <div className="grid grid-cols-2 gap-2.5">
                {WORKSPACE_TEMPLATES.map((t) => {
                  const active = templateId === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => onPickTemplate(t)}
                      className={cn(
                        "group relative flex flex-col gap-1.5 rounded-xl border bg-surface-1 p-3.5 text-left transition-all duration-150",
                        active
                          ? "border-accent/40 bg-accent-soft shadow-[0_0_0_3px_oklch(0.68_0.19_280/0.10)]"
                          : "border-border hover:border-border-hover hover:bg-surface-2",
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "grid h-8 w-8 shrink-0 place-items-center rounded-lg",
                            active
                              ? "bg-accent text-white"
                              : "bg-surface-2 text-accent",
                          )}
                        >
                          {TEMPLATE_ICONS[t.icon] || (
                            <Layers size={16} />
                          )}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-[13px] font-semibold text-text-primary">
                            {t.title}
                          </div>
                          <div className="truncate text-[11px] text-text-muted">
                            {t.tagline}
                          </div>
                        </div>
                        {active && (
                          <Check size={14} className="shrink-0 text-accent" />
                        )}
                      </div>
                      <p className="line-clamp-2 text-[11.5px] leading-relaxed text-text-muted">
                        {t.description}
                      </p>
                    </button>
                  );
                })}
              </div>
            </section>

            <section className="mb-7">
              <SectionLabel className="mb-2">2 · Trigger & severity</SectionLabel>
              <p className="mb-3 text-[12px] text-text-muted">
                Attribute this investigation to its source — used for routing,
                audit, and post-mortems.
              </p>
              <div className="grid grid-cols-[1fr_auto] gap-3">
                <div>
                  <label className="mb-1.5 block text-[10.5px] font-semibold uppercase tracking-wider text-text-muted">
                    Trigger
                  </label>
                  <div className="flex flex-wrap gap-1">
                    {TRIGGER_OPTIONS.map((opt) => {
                      const active = trigger === opt.id;
                      return (
                        <button
                          key={opt.id}
                          onClick={() => setTrigger(opt.id)}
                          className={cn(
                            "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-[12px] transition-colors",
                            active
                              ? "border-accent/40 bg-accent-soft text-accent"
                              : "border-border bg-surface-2 text-text-secondary hover:bg-surface-3",
                          )}
                        >
                          {opt.icon}
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                  <input
                    value={triggerRef}
                    onChange={(e) => setTriggerRef(e.target.value)}
                    placeholder="External reference (e.g. INC-91204, T-10243) — optional"
                    className="mt-2 h-9 w-full rounded-md border border-border bg-surface-2 px-3 font-mono text-[12px] text-text-primary placeholder:text-text-muted focus:border-accent"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-[10.5px] font-semibold uppercase tracking-wider text-text-muted">
                    Severity
                  </label>
                  <div className="flex flex-col gap-1">
                    {SEVERITY_ORDER.map((sev) => {
                      const active = severity === sev;
                      return (
                        <button
                          key={sev}
                          onClick={() => setSeverity(sev)}
                          className={cn(
                            "inline-flex items-center gap-2 rounded-md border px-2.5 py-1.5 text-left transition-colors",
                            active
                              ? "border-accent/40 bg-accent-soft text-accent"
                              : "border-border bg-surface-2 text-text-secondary hover:bg-surface-3",
                          )}
                          title={SEVERITY_DESCRIPTIONS[sev]}
                        >
                          <span className="font-mono text-[12px] font-semibold">
                            {sev}
                          </span>
                          <span className="text-[10.5px] text-text-muted">
                            {sev === "P1"
                              ? "Critical"
                              : sev === "P2"
                                ? "Major"
                                : sev === "P3"
                                  ? "Moderate"
                                  : "Minor"}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            </section>

            <section className="mb-7">
              <SectionLabel className="mb-2">3 · Agent authority</SectionLabel>
              <p className="mb-3 text-[12px] text-text-muted">
                Governs what the agent can do without checking in. The default
                follows the template; tighten it for sensitive runs.
              </p>
              <div className="flex flex-col gap-1.5">
                {AUTHORITY_OPTIONS.map((opt) => {
                  const active = authority === opt.id;
                  return (
                    <button
                      key={opt.id}
                      onClick={() => setAuthority(opt.id)}
                      className={cn(
                        "flex items-start gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors",
                        active
                          ? "border-accent/40 bg-accent-soft"
                          : "border-border bg-surface-1 hover:border-border-hover hover:bg-surface-2",
                      )}
                    >
                      <span
                        className={cn(
                          "mt-0.5 grid h-4 w-4 shrink-0 place-items-center rounded-full border-2",
                          active
                            ? "border-accent bg-accent"
                            : "border-border-hover bg-surface-2",
                        )}
                      >
                        {active && (
                          <span className="h-1.5 w-1.5 rounded-full bg-white" />
                        )}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div
                          className={cn(
                            "text-[13px] font-semibold",
                            active ? "text-accent" : "text-text-primary",
                          )}
                        >
                          {opt.label}
                        </div>
                        <div className="text-[11.5px] text-text-muted">
                          {opt.description}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>

            <section className="mb-7">
              <SectionLabel className="mb-2">4 · Mounts</SectionLabel>
              <p className="mb-3 text-[12px] text-text-muted">
                Mirage will only expose these paths to the agent. Read/write is
                governed by the template.
              </p>
              <div className="grid grid-cols-2 gap-1.5">
                {template.mounts.map((mount) => {
                  const enabled = mounts.includes(mount.path);
                  return (
                    <button
                      key={mount.path}
                      onClick={() => toggleMount(mount.path)}
                      className={cn(
                        "inline-flex items-center justify-between gap-2 rounded-md border px-2.5 py-1.5 text-left transition-colors",
                        enabled
                          ? "border-accent/40 bg-accent-soft"
                          : "border-border bg-surface-2 hover:bg-surface-3",
                      )}
                    >
                      <span className="flex items-center gap-2 font-mono text-[11.5px] text-text-primary">
                        <span
                          className={cn(
                            "h-1.5 w-1.5 rounded-full",
                            enabled ? "bg-accent" : "bg-text-faint",
                          )}
                        />
                        {mount.path}
                      </span>
                      <Badge
                        tone={mount.mode === "rw" ? "warning" : "neutral"}
                        size="xs"
                        mono
                      >
                        {mount.mode}
                      </Badge>
                    </button>
                  );
                })}
              </div>
              <div className="mt-2 text-[10.5px] text-text-faint">
                Tools available to this run:{" "}
                <span className="font-mono text-text-muted">
                  {template.tools.join(", ")}
                </span>
              </div>
            </section>

            <section className="mb-7">
              <SectionLabel className="mb-2">5 · Brief the agent</SectionLabel>
              <p className="mb-3 text-[12px] text-text-muted">
                One-sentence title and a clear description of the desired
                outcome. The agent will treat this as the goal.
              </p>
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Investigation title (optional — auto-generated from brief)"
                className="mb-2 h-9 w-full rounded-md border border-border bg-surface-2 px-3 text-[12.5px] text-text-primary placeholder:text-text-muted focus:border-accent"
              />
              <textarea
                value={brief}
                onChange={(e) => setBrief(e.target.value)}
                placeholder={template.promptHint}
                rows={5}
                className="block w-full resize-none rounded-md border border-border bg-surface-2 px-3 py-2.5 text-[13px] leading-relaxed text-text-primary placeholder:text-text-muted focus:border-accent"
              />
              {error && (
                <div className="mt-2 rounded-md border border-danger/30 bg-danger-soft px-2.5 py-1.5 text-[11.5px] text-danger">
                  {error}
                </div>
              )}
            </section>
          </div>
        </div>

        <aside className="flex min-w-0 flex-col border-l border-border bg-surface-1/40">
          <div className="border-b border-border px-5 py-4">
            <SectionLabel className="mb-2">Run summary</SectionLabel>
            <div className="space-y-3 text-[12px]">
              <SummaryRow label="Template" value={template.title} />
              <SummaryRow
                label="Severity"
                value={severity}
                mono
                tone={
                  severity === "P1"
                    ? "text-danger"
                    : severity === "P2"
                      ? "text-warning"
                      : "text-text-primary"
                }
              />
              <SummaryRow
                label="Trigger"
                value={
                  TRIGGER_OPTIONS.find((o) => o.id === trigger)?.label || trigger
                }
                detail={triggerRef || undefined}
              />
              <SummaryRow
                label="Authority"
                value={
                  AUTHORITY_OPTIONS.find((o) => o.id === authority)?.label ||
                  authority
                }
                tone={
                  authority === "autonomous"
                    ? "text-danger"
                    : authority === "approve_writes"
                      ? "text-warning"
                      : "text-accent"
                }
              />
              <SummaryRow
                label="Mounts"
                value={`${mounts.length} path${mounts.length === 1 ? "" : "s"}`}
                detail={mounts.join(", ")}
              />
            </div>
          </div>

          <div className="border-b border-border px-5 py-4">
            <SectionLabel className="mb-2">Budget caps</SectionLabel>
            <div className="space-y-2 text-[12px]">
              <BudgetRow
                label="Tokens"
                value={`${(template.budget.tokens / 1000).toFixed(0)}k`}
              />
              <BudgetRow
                label="Wallclock"
                value={`${template.budget.wallclockMin} min`}
              />
              <BudgetRow
                label="Tool calls"
                value={template.budget.toolCalls.toString()}
              />
            </div>
          </div>

          <div className="mt-auto border-t border-border px-5 py-4">
            <button
              onClick={handleDispatch}
              disabled={!canSubmit}
              className={cn(
                "inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg text-[13px] font-semibold transition-colors",
                canSubmit
                  ? "bg-accent text-white shadow-sm hover:bg-accent-hover"
                  : "cursor-not-allowed bg-surface-3 text-text-muted",
              )}
            >
              {submitting ? (
                <>
                  <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" />
                  Dispatching…
                </>
              ) : (
                <>
                  <Send size={14} />
                  Dispatch investigation
                  <ArrowRight size={14} />
                </>
              )}
            </button>
            <p className="mt-2 text-[10.5px] leading-relaxed text-text-faint">
              On dispatch we create a session, hydrate the Mirage workspace,
              and stream you into the investigation in real time.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

function SummaryRow({
  label,
  value,
  detail,
  mono,
  tone,
}: {
  label: string;
  value: string;
  detail?: string;
  mono?: boolean;
  tone?: string;
}) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <span className="text-text-muted">{label}</span>
        <span
          className={cn(
            "text-right font-semibold text-text-primary",
            mono && "font-mono",
            tone,
          )}
        >
          {value}
        </span>
      </div>
      {detail && (
        <div className="mt-0.5 truncate text-right font-mono text-[10.5px] text-text-faint">
          {detail}
        </div>
      )}
    </div>
  );
}

function BudgetRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-text-muted">{label}</span>
      <span className="font-mono text-text-primary">{value}</span>
    </div>
  );
}
