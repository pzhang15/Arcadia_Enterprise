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

export interface StreamEvent {
  type: string;
  timestamp: number;
  session_id?: string;
  [key: string]: unknown;
}

export interface CommandEvent {
  type: "command";
  agent: string;
  session: string;
  timestamp: number;
  command: string;
  exit_code: number;
  stdout: string | null;
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
}
