import { useMemo } from "react";
import { ArrowDownToLine, FileDown, Globe } from "lucide-react";
import type { VfsOp } from "@/types/agui";
import type { CaptureState, ConsoleMount, EffectClass } from "@/types/console";
import { EFFECT_DEFAULT_CAPTURE } from "@/lib/captureState";
import { mountBgClass, mountKey } from "@/lib/mountColor";
import { cn, formatBytes } from "@/lib/utils";
import { CaptureBadge } from "./CaptureBadge";
import { EffectClassTag } from "./EffectClassTag";

const WRITE_OPS = new Set([
  "write",
  "append",
  "truncate",
  "create",
  "mkdir",
  "rename",
  "unlink",
  "rmdir",
]);

interface MountGroup {
  prefix: string;
  effectClass: EffectClass;
  reads: number;
  readBytes: number;
  writes: VfsOp[];
}

function effectFor(prefix: string, mounts: ConsoleMount[]): EffectClass {
  const direct = mounts.find((m) => m.prefix === prefix);
  if (direct) return direct.effect_class;
  const key = mountKey(prefix);
  const byKey = mounts.find((m) => mountKey(m.prefix) === key);
  return byKey?.effect_class ?? "durable-internal";
}

function captureFor(effectClass: EffectClass): CaptureState {
  return EFFECT_DEFAULT_CAPTURE[effectClass];
}

interface Props {
  vfsOps: VfsOp[];
  mounts: ConsoleMount[];
}

export function LiveWorldPanel({ vfsOps, mounts }: Props) {
  const groups = useMemo(() => {
    const map = new Map<string, MountGroup>();
    for (const op of vfsOps) {
      const prefix = op.mount_prefix || "/";
      let g = map.get(prefix);
      if (!g) {
        g = {
          prefix,
          effectClass: effectFor(prefix, mounts),
          reads: 0,
          readBytes: 0,
          writes: [],
        };
        map.set(prefix, g);
      }
      if (WRITE_OPS.has(op.op)) {
        g.writes.push(op);
      } else {
        g.reads += 1;
        g.readBytes += op.bytes || 0;
      }
    }
    return [...map.values()].sort((a, b) => b.writes.length - a.writes.length);
  }, [vfsOps, mounts]);

  const totalWrites = groups.reduce((n, g) => n + g.writes.length, 0);

  if (vfsOps.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
        <Globe size={22} className="text-text-faint" />
        <p className="text-[12px] text-text-muted">
          No world interactions yet.
        </p>
        <p className="max-w-[220px] text-[11px] text-text-faint">
          Every read the agent makes is observed; every write is captured into
          the overlay — nothing reaches the real service.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <span className="text-[11px] font-medium text-text-secondary">
          Live world · overlay
        </span>
        <span className="font-mono text-[10px] text-text-muted tabular-nums">
          {totalWrites} captured · {vfsOps.length} ops
        </span>
      </div>
      <div className="scrollbar-thin flex-1 overflow-y-auto p-2.5">
        <div className="flex flex-col gap-2.5">
          {groups.map((g) => (
            <div
              key={g.prefix}
              className="overflow-hidden rounded-lg border border-border bg-surface-1/60"
            >
              <div className="flex items-center gap-2 border-b border-border/60 px-2.5 py-1.5">
                <span className={cn("h-2 w-2 shrink-0 rounded-full", mountBgClass(g.prefix))} />
                <span className="truncate font-mono text-[11px] text-text-primary">
                  {g.prefix}
                </span>
                <EffectClassTag effectClass={g.effectClass} className="ml-0.5" />
                <span className="ml-auto flex items-center gap-1.5 font-mono text-[10px] text-text-faint tabular-nums">
                  <ArrowDownToLine size={11} /> {g.reads}
                </span>
              </div>
              {g.writes.length === 0 ? (
                <div className="px-2.5 py-1.5 text-[10px] text-text-faint">
                  read-only so far
                </div>
              ) : (
                <ul className="divide-y divide-border/50">
                  {g.writes.slice(-12).map((op, i) => (
                    <li
                      key={`${op.path}-${op.timestamp}-${i}`}
                      className="flex items-center gap-2 px-2.5 py-1.5"
                    >
                      <FileDown size={12} className="shrink-0 text-text-muted" />
                      <span className="truncate font-mono text-[11px] text-text-secondary">
                        {op.path}
                      </span>
                      <CaptureBadge
                        state={captureFor(g.effectClass)}
                        size="xs"
                        flash
                        className="ml-auto"
                      />
                      <span className="w-12 shrink-0 text-right font-mono text-[10px] text-text-faint tabular-nums">
                        {formatBytes(op.bytes || 0)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
