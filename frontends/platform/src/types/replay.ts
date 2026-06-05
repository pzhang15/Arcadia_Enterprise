export interface ReplayAction {
  idx: number;
  op: string;
  path: string;
  source: string;
  bytes: number;
  duration_ms: number;
  mount_prefix: string | null;
  fingerprint: string | null;
  revision: string | null;
  is_cache: boolean;
  tool_call_id: string | null;
  run_id: string | null;
  timestamp: number;
}

export interface ReplayOverlayChange {
  path: string;
  op: string;
  bytes: number;
  mount_prefix: string | null;
}

export interface ReplayDiff {
  kind: "read" | "write";
  path: string;
  added_bytes?: number;
  mount_prefix?: string | null;
  source?: string;
  is_cache?: boolean;
  fingerprint?: string | null;
  revision?: string | null;
}

export interface ReplayState {
  overlay: ReplayOverlayChange[];
  reads_so_far: string[];
  reads_count: number;
  cursor_op: ReplayAction | null;
  diff: ReplayDiff | null;
}

export interface ReplayResponse {
  session_id: string;
  run_id: string | null;
  cursor: number;
  total: number;
  actions: ReplayAction[];
  state: ReplayState;
}
