export type InvestigationStatus =
  | "queued"
  | "running"
  | "needs_review"
  | "resolved"
  | "escalated"
  | "cancelled";

export type InvestigationSeverity = "P1" | "P2" | "P3" | "P4";

export type InvestigationTrigger =
  | "manual"
  | "alert"
  | "ticket"
  | "customer"
  | "scheduled"
  | "compliance";

export type InvestigationAuthority = "read_only" | "approve_writes" | "autonomous";

export interface InvestigationMeta {
  sessionId: string;
  title: string;
  templateId: string;
  severity: InvestigationSeverity;
  status: InvestigationStatus;
  trigger: InvestigationTrigger;
  triggerRef?: string;
  authority: InvestigationAuthority;
  brief?: string;
  resolution?: string;
  resolvedAt?: number;
  escalatedTo?: string;
  createdAt: number;
  updatedAt: number;
}

export const STATUS_ORDER: InvestigationStatus[] = [
  "running",
  "queued",
  "needs_review",
  "escalated",
  "resolved",
  "cancelled",
];

export const SEVERITY_ORDER: InvestigationSeverity[] = ["P1", "P2", "P3", "P4"];

export const TRIGGER_LABELS: Record<InvestigationTrigger, string> = {
  manual: "Manual",
  alert: "Alert",
  ticket: "Ticket",
  customer: "Customer",
  scheduled: "Scheduled",
  compliance: "Compliance",
};

export const STATUS_LABELS: Record<InvestigationStatus, string> = {
  queued: "Queued",
  running: "Running",
  needs_review: "Needs review",
  resolved: "Resolved",
  escalated: "Escalated",
  cancelled: "Cancelled",
};

export const AUTHORITY_LABELS: Record<InvestigationAuthority, string> = {
  read_only: "Read-only",
  approve_writes: "Writes need approval",
  autonomous: "Autonomous",
};

export const SEVERITY_DESCRIPTIONS: Record<InvestigationSeverity, string> = {
  P1: "Critical · customer-facing outage or compliance breach",
  P2: "Major · degraded service, escalating impact",
  P3: "Moderate · investigation needed, limited blast radius",
  P4: "Minor · cleanup, review, or routine task",
};
