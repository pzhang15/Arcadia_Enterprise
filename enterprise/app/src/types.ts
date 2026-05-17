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
