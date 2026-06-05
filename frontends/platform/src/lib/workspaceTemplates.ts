import type {
  InvestigationAuthority,
  InvestigationSeverity,
  InvestigationTrigger,
} from "@/types/investigation";

export interface WorkspaceTemplate {
  id: string;
  title: string;
  tagline: string;
  description: string;
  services: string[];
  mounts: { path: string; mode: "ro" | "rw" }[];
  tools: string[];
  defaultAuthority: InvestigationAuthority;
  defaultSeverity: InvestigationSeverity;
  defaultTrigger: InvestigationTrigger;
  promptHint: string;
  budget: {
    tokens: number;
    wallclockMin: number;
    toolCalls: number;
  };
  icon: string;
}

export const WORKSPACE_TEMPLATES: WorkspaceTemplate[] = [
  {
    id: "incident-response",
    title: "Incident Response",
    tagline: "Production outage triage",
    description:
      "Cross-reference PagerDuty incidents with engineering deploys, error logs, and recent commits. Proposes mitigations; writes require approval.",
    services: ["engineering", "it"],
    mounts: [
      { path: "/pagerduty", mode: "ro" },
      { path: "/datadog", mode: "ro" },
      { path: "/github", mode: "ro" },
      { path: "/scratch", mode: "rw" },
    ],
    tools: ["vfs.read", "vfs.search", "mcp.pagerduty", "mcp.datadog", "shell.exec"],
    defaultAuthority: "approve_writes",
    defaultSeverity: "P1",
    defaultTrigger: "alert",
    promptHint:
      "Investigate the active P1: identify root cause, summarize blast radius, and propose an immediate mitigation. Cite incident IDs and recent deploys.",
    budget: { tokens: 60000, wallclockMin: 10, toolCalls: 80 },
    icon: "zap",
  },
  {
    id: "customer-escalation",
    title: "Customer Escalation",
    tagline: "High-touch account investigation",
    description:
      "Pull every signal we have on an account: open tickets, recent escalations, contract terms, health score history. Drafts a CSM brief.",
    services: ["customer-support", "it", "finance"],
    mounts: [
      { path: "/customers", mode: "ro" },
      { path: "/tickets", mode: "ro" },
      { path: "/slack", mode: "ro" },
      { path: "/scratch", mode: "rw" },
    ],
    tools: ["vfs.read", "vfs.search", "mcp.salesforce", "mcp.zendesk"],
    defaultAuthority: "read_only",
    defaultSeverity: "P2",
    defaultTrigger: "customer",
    promptHint:
      "Compile a 360 on the named account. Recent tickets, escalations, contract terms, churn risk. End with a 3-bullet brief for the CSM.",
    budget: { tokens: 40000, wallclockMin: 8, toolCalls: 60 },
    icon: "headphones",
  },
  {
    id: "compliance-review",
    title: "Compliance Review",
    tagline: "Audit-readiness sweep",
    description:
      "Scan contracts, policy acknowledgments, and audit checklists against a named framework (SOC2, ISO 27001, GDPR). Read-only by design.",
    services: ["compliance", "hr"],
    mounts: [
      { path: "/compliance", mode: "ro" },
      { path: "/hr", mode: "ro" },
      { path: "/finance", mode: "ro" },
    ],
    tools: ["vfs.read", "vfs.search"],
    defaultAuthority: "read_only",
    defaultSeverity: "P3",
    defaultTrigger: "compliance",
    promptHint:
      "Run a SOC2 readiness check: list every control with its current evidence, flag gaps, suggest remediation owners.",
    budget: { tokens: 80000, wallclockMin: 15, toolCalls: 120 },
    icon: "shield-check",
  },
  {
    id: "ticket-triage",
    title: "Ticket Triage",
    tagline: "Helpdesk queue sweep",
    description:
      "Classify and route open helpdesk tickets: detect duplicates, propose priority, auto-tag, and surface the ones that need a human.",
    services: ["it", "hr"],
    mounts: [
      { path: "/tickets", mode: "ro" },
      { path: "/slack", mode: "ro" },
      { path: "/scratch", mode: "rw" },
    ],
    tools: ["vfs.read", "vfs.search", "mcp.zendesk"],
    defaultAuthority: "approve_writes",
    defaultSeverity: "P3",
    defaultTrigger: "scheduled",
    promptHint:
      "Walk the open IT queue. For each ticket: classify priority, flag duplicates, suggest assignee. End with a queue-health summary.",
    budget: { tokens: 50000, wallclockMin: 10, toolCalls: 100 },
    icon: "ticket-check",
  },
  {
    id: "exec-brief",
    title: "Cross-functional Brief",
    tagline: "Executive readout",
    description:
      "Pull cross-departmental signal — IT, Finance, Customers, Compliance — and synthesize a single executive-grade brief.",
    services: ["it", "finance", "customer-support", "compliance", "engineering"],
    mounts: [
      { path: "/tickets", mode: "ro" },
      { path: "/finance", mode: "ro" },
      { path: "/customers", mode: "ro" },
      { path: "/compliance", mode: "ro" },
      { path: "/pagerduty", mode: "ro" },
      { path: "/scratch", mode: "rw" },
    ],
    tools: ["vfs.read", "vfs.search", "shell.exec"],
    defaultAuthority: "read_only",
    defaultSeverity: "P3",
    defaultTrigger: "manual",
    promptHint:
      "Synthesize a 7-day cross-functional health brief: top risks, customer escalations, financial exceptions, compliance deltas.",
    budget: { tokens: 100000, wallclockMin: 20, toolCalls: 150 },
    icon: "layers",
  },
  {
    id: "custom",
    title: "Custom Workspace",
    tagline: "Bring your own mounts",
    description:
      "Hand-pick mounts and authority for ad-hoc tasks. Use when none of the templates fit.",
    services: [],
    mounts: [{ path: "/scratch", mode: "rw" }],
    tools: ["vfs.read", "vfs.search"],
    defaultAuthority: "read_only",
    defaultSeverity: "P3",
    defaultTrigger: "manual",
    promptHint: "Describe the task in your own words.",
    budget: { tokens: 30000, wallclockMin: 5, toolCalls: 50 },
    icon: "sliders",
  },
];

export function findTemplate(id: string): WorkspaceTemplate {
  return (
    WORKSPACE_TEMPLATES.find((t) => t.id === id) || WORKSPACE_TEMPLATES[0]
  );
}
