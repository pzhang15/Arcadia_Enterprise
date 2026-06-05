export type WorkspaceMode = "TEST" | "LIVE";

export type WorkspaceStatus = "created" | "ready" | "error";

export type EffectClass =
  | "scratch"
  | "durable-internal"
  | "system-of-record"
  | "external-effect";

export type CaptureState = "captured" | "simulated" | "live";

export type MountMode = "ro" | "rw";

export interface MountSpec {
  path: string;
  mode: MountMode;
}

export interface ConsoleMount {
  prefix: string;
  resource: string;
  mode: string;
  effect_class: EffectClass;
}

export interface SnapshotEntry {
  name: string;
  path: string;
  size: number;
  created_at: number;
}

export interface ConsoleWorkspaceBrief {
  id: string;
  name: string;
  template_id: string;
  mode: WorkspaceMode;
  branch: string;
  parent_id: string | null;
  status: WorkspaceStatus;
  mount_count: number;
  pending_effects: number;
  created_at: number;
}

export interface ConsoleWorkspaceDetail extends ConsoleWorkspaceBrief {
  mounts: ConsoleMount[];
  snapshots: SnapshotEntry[];
  pinned_backing: boolean;
  error: string | null;
}

export interface PendingEffect {
  key: string;
  op: string;
  path: string;
  mount_prefix: string;
  source: string;
  bytes: number;
  effect_class: EffectClass;
  capture_state: CaptureState;
  target: string;
  reversibility: string;
  promoted: boolean;
  timestamp: number;
}

export interface OverlayChange {
  key: string;
  op: string;
  path: string;
  bytes: number;
  timestamp: number;
}

export interface OverlayMount {
  prefix: string;
  resource: string;
  mode: string;
  effect_class: EffectClass;
  changes: OverlayChange[];
}

export interface OverlayDiff {
  mounts: OverlayMount[];
}

export type TrajectoryKind = "read" | "write" | "meta";

export interface TrajectoryEntry {
  idx: number;
  op: string;
  kind: TrajectoryKind;
  path: string;
  mount_prefix: string;
  source: string;
  bytes: number;
  duration_ms: number;
  timestamp: number;
  effect_class: EffectClass;
  capture_state: CaptureState | null;
}

export interface DryRunMount {
  path: string;
  mode: MountMode;
  effect_class: EffectClass;
  exists: boolean;
  bytes: number;
  files: number;
}

export interface DryRunResult {
  workspace_id: string;
  mounts: DryRunMount[];
  estimated_snapshot_bytes: number;
  estimated_files: number;
  cache_plan: string;
}

export interface PromoteResultEntry {
  key: string;
  status: "promoted" | "missing";
  effect_class?: EffectClass;
  simulated?: boolean;
}

export interface PromoteResult {
  results: PromoteResultEntry[];
  promoted_total: number;
  pending: number;
  simulated: boolean;
}

export interface TestRunStep {
  command: string;
  exit_code: number;
  stdout: string;
  op_count: number;
  wrote: boolean;
  ok: boolean;
}

export interface TestRunPermission {
  prefix: string;
  mode: string;
  effect_class: EffectClass;
  writable: boolean;
  expected_writable: boolean;
  enforced: boolean;
}

export interface TestRunResult {
  workspace_id: string;
  ok: boolean;
  steps: TestRunStep[];
  permissions: TestRunPermission[];
  captured_writes: number;
}

export const EFFECT_CLASS_LABELS: Record<EffectClass, string> = {
  scratch: "Scratch",
  "durable-internal": "Durable internal",
  "system-of-record": "System of record",
  "external-effect": "External effect",
};

export const EFFECT_CLASS_ORDER: EffectClass[] = [
  "external-effect",
  "system-of-record",
  "durable-internal",
  "scratch",
];

export const CAPTURE_STATE_LABELS: Record<CaptureState, string> = {
  captured: "CAPTURED",
  simulated: "SIMULATED",
  live: "LIVE",
};

export function defaultCaptureState(effectClass: EffectClass): CaptureState {
  return effectClass === "external-effect" ? "simulated" : "captured";
}
