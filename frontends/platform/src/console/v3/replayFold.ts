import type { ReplayAction, ReplayState } from "@/types/replay";

const WRITE_OPS = new Set([
  "write",
  "append",
  "create",
  "truncate",
  "unlink",
  "rename",
]);
const READ_OPS = new Set(["read", "stream"]);

const LIVE_RE = /\b(live|latest|current|production|prod|fresh|today)\b/i;
const STALE_RE = /(20(1\d|2[0-3])|staging|backup|archive|_old|_bak)/i;

export function foldReplay(actions: ReplayAction[], cursor: number): ReplayState {
  const overlay = new Map<string, ReplayState["overlay"][number]>();
  const reads = new Set<string>();
  const upto = cursor < 0 ? [] : actions.slice(0, cursor + 1);
  for (const a of upto) {
    if (WRITE_OPS.has(a.op)) {
      overlay.set(a.path, {
        path: a.path,
        op: a.op,
        bytes: a.bytes,
        mount_prefix: a.mount_prefix,
      });
    } else if (READ_OPS.has(a.op)) {
      reads.add(a.path);
    }
  }
  const cur = cursor >= 0 && cursor < actions.length ? actions[cursor] : null;
  let diff: ReplayState["diff"] = null;
  if (cur && WRITE_OPS.has(cur.op)) {
    diff = {
      kind: "write",
      path: cur.path,
      added_bytes: cur.bytes,
      mount_prefix: cur.mount_prefix,
    };
  } else if (cur) {
    diff = {
      kind: "read",
      path: cur.path,
      source: cur.source,
      is_cache: cur.is_cache,
      fingerprint: cur.fingerprint,
      revision: cur.revision,
    };
  }
  return {
    overlay: [...overlay.values()],
    reads_so_far: [...reads].sort(),
    reads_count: reads.size,
    cursor_op: cur,
    diff,
  };
}

export function groupActionsByToolCall(
  actions: ReplayAction[],
): Map<string, ReplayAction[]> {
  const m = new Map<string, ReplayAction[]>();
  for (const a of actions) {
    const k = a.tool_call_id || "__unlinked__";
    const arr = m.get(k);
    if (arr) arr.push(a);
    else m.set(k, [a]);
  }
  return m;
}

export interface IntentFlag {
  mismatch: boolean;
  reason: string;
}

export function intentEffectFlag(
  reasoning: string | undefined,
  action: ReplayAction,
): IntentFlag {
  if (!reasoning || !LIVE_RE.test(reasoning)) {
    return { mismatch: false, reason: "" };
  }
  if (action.is_cache) {
    return {
      mismatch: true,
      reason: `"live" intent but cached read of ${action.path}`,
    };
  }
  if (STALE_RE.test(action.path)) {
    return {
      mismatch: true,
      reason: `"live" intent vs a stale-looking path ${action.path}`,
    };
  }
  return { mismatch: false, reason: "" };
}
