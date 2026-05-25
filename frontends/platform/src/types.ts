export interface McpToolCallEvent {
  type: "mcp_tool_call";
  timestamp: number;
  tool: string;
  arguments: Record<string, unknown>;
  result: string;
  result_bytes: number;
  duration_ms: number;
  error: string | null;
}

export interface MockRequestEvent {
  type: "mock_request";
  timestamp: number;
  service: string;
  method: string;
  path: string;
  query: Record<string, unknown>;
  status_code: number;
  response_bytes: number;
  duration_ms: number;
}

export interface CommandEvent {
  type: "command";
  agent: string;
  session: string;
  timestamp: number;
  command: string;
  exit_code: number;
  stdout: string | null;
  cwd?: string | null;
}

export interface OpEvent {
  type: "op";
  agent: string;
  session: string;
  timestamp: number;
  op: string;
  path: string;
  source: string;
  bytes: number;
  duration_ms: number;
  mount_prefix?: string;
  fingerprint?: string | null;
  revision?: string | null;
}

export type StreamEvent =
  | McpToolCallEvent
  | MockRequestEvent
  | CommandEvent
  | OpEvent;

export interface GateResult {
  name: string;
  passed: boolean;
  detail: string;
}

export interface ProgrammaticResult {
  gates: GateResult[];
  fraction_passed: number;
  all_passed: boolean;
  by_category: Record<string, number>;
}

export interface TrajectoryMetrics {
  n_turns: number;
  n_commands: number;
  n_ops: number;
  n_unique_paths?: number;
  bytes_read: number;
  bytes_written?: number;
  cache_hit_rate: number;
  wallclock_s: number;
  tokens_in: number;
  tokens_out: number;
  requests?: number;
  cost_usd: number;
  within_budget: boolean;
  budget_breaches?: string[];
}

export interface JudgeResult {
  scores: Record<string, number>;
  rationale: Record<string, string>;
  weighted: number;
  error: string | null;
}

export interface ScoreCard {
  scenario_id: string;
  task_id: string;
  surface: string;
  model: string;
  seed: number;
  sweep_id: string;
  passed_gates: boolean;
  programmatic: ProgrammaticResult;
  trajectory: TrajectoryMetrics;
  judge: JudgeResult;
  composite: number;
  failure_modes: string[];
  error: string | null;
}

export interface CellSummary {
  n_runs: number;
  n_passed_gates: number;
  composite_mean: number;
  composite_max: number;
  judge_mean: number;
  cost_usd_total: number;
  wallclock_s_p95: number;
  failure_modes: Record<string, number>;
}

export interface AggregateReport {
  sweep_id: string;
  scenario_id: string;
  surface: string;
  models: string[];
  seeds: number[];
  tasks: string[];
  n_runs: number;
  n_succeeded: number;
  composite_mean: number;
  composite_by_task: Record<string, number>;
  composite_by_model: Record<string, number>;
  cell_by_model_task: Record<string, Record<string, CellSummary>>;
  failure_modes: Record<string, number>;
  runs: ScoreCard[];
}

export interface SweepInfo {
  scenario: string;
  sweep_id: string;
  path: string;
}

export interface MountStats {
  mount: string;
  reads: number;
  writes: number;
  bytes: number;
  ops: OpEvent[];
}

export interface SpanMetrics {
  bytes_read: number;
  bytes_written: number;
  api_calls: number;
  cache_hits: number;
  cache_misses: number;
}

export interface SpanEvent {
  span_id: string;
  timestamp_ms: number;
  name: string;
  attributes: Record<string, unknown>;
}

export interface TraceSpan {
  trace_id: string;
  span_id: string;
  parent_span_id: string | null;
  name: string;
  kind: number;
  start_time_ms: number;
  end_time_ms: number;
  status: number;
  level: number;
  attributes: Record<string, unknown>;
  metrics: SpanMetrics;
  session_id: string;
  agent_id: string;
  events: SpanEvent[];
}

export interface TraceDetail {
  trace_id: string;
  spans: TraceSpan[];
}

export interface TraceSummary {
  trace_id: string;
  name: string;
  start_time_ms: number;
  end_time_ms: number;
  status: number;
  attributes: Record<string, unknown>;
  metrics: SpanMetrics;
  session_id: string;
  agent_id: string;
  child_count: number;
}

export interface Employee {
  id: string;
  handle: string;
  name: string;
  email: string;
  title: string;
  department?: string;
}

export interface Ticket {
  ticket_id: string;
  subject: string;
  body: string;
  requester: { id: string; name: string; email: string };
  assignee: { id: string; name: string; email: string } | null;
  queue: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at: string;
  tags: string[];
  related_tickets: string[];
  comments: { author: string; ts: string; body: string }[];
}

export interface Expense {
  expense_id: string;
  submitter: { id: string; name: string; email: string };
  department: string;
  amount: number;
  currency: string;
  category: string;
  description: string;
  submitted_at: string;
  status: string;
  approver: string | null;
  line_items: { description: string; amount: number }[];
}

export interface PurchaseOrder {
  po_id: string;
  requester: { id: string; name: string; email: string };
  vendor: string;
  items: { description: string; quantity: number; unit_price: number }[];
  total: number;
  status: string;
  created_at: string;
  approved_by: string | null;
  department: string;
}

export interface Invoice {
  invoice_id: string;
  vendor: string;
  amount: number;
  due_date: string;
  po_reference: string | null;
  status: string;
  department: string;
}

export interface CustomerAccount {
  account_id: string;
  company_name: string;
  tier: string;
  arr: number;
  health_score: number;
  csm: string;
  renewal_date: string;
  contacts: { name: string; email: string; role: string }[];
  products: string[];
}

export interface Escalation {
  escalation_id: string;
  account_id: string;
  severity: string;
  description: string;
  linked_ticket: string;
  created_at: string;
  status: string;
  owner: string;
}

export interface Contract {
  contract_id: string;
  counterparty: string;
  type: string;
  value: number;
  start_date: string;
  end_date: string;
  status: string;
  owner: string;
  review_notes: string;
}

export interface Audit {
  audit_id: string;
  framework: string;
  status: string;
  due_date: string;
  checklist: { name: string; status: string; owner: string; evidence_link: string }[];
}

export interface Policy {
  policy_id: string;
  title: string;
  version: string;
  effective_date: string;
  acknowledgments: { user_id: string; acked_at: string | null }[];
}

export interface PagerDutyIncident {
  id: string;
  title: string;
  status: string;
  severity: string;
  service: string;
  assignee: string;
  created_at: string;
}

export interface Deployment {
  id: string;
  ref: string;
  environment: string;
  created_at: string;
  status: string;
  creator: string;
}

export interface BudgetData {
  departments: { name: string; budget: number; spent: number; remaining: number; status: string }[];
}

export interface AgentSession {
  id: string;
  status: "created" | "running" | "completed" | "error";
  task: string;
  services: string[];
  created_at: number;
  completed_at: number | null;
  error: string | null;
}

export interface AgentResult {
  summary: string;
  services_touched: Record<string, number>;
  files_created: Record<string, string>;
  commands_run: number;
  duration_s: number;
}

export interface QuickAction {
  id: string;
  label: string;
  services: string[];
  task: string;
}
