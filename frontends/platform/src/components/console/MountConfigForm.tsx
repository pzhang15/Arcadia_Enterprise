import { Plus, Trash2 } from "lucide-react";
import type { MountMode, MountSpec } from "@/types/console";
import { effectClassForPrefix } from "@/lib/effectClass";
import { cn } from "@/lib/utils";
import { EffectClassTag } from "./EffectClassTag";

interface Props {
  mounts: MountSpec[];
  onChange: (mounts: MountSpec[]) => void;
}

export function MountConfigForm({ mounts, onChange }: Props) {
  function update(i: number, patch: Partial<MountSpec>) {
    onChange(mounts.map((m, idx) => (idx === i ? { ...m, ...patch } : m)));
  }
  function remove(i: number) {
    onChange(mounts.filter((_, idx) => idx !== i));
  }
  function add() {
    onChange([...mounts, { path: "/scratch", mode: "rw" }]);
  }

  return (
    <div className="flex flex-col gap-2">
      {mounts.map((m, i) => (
        <div
          key={i}
          className="flex items-center gap-2 rounded-lg border border-border bg-surface-1 px-2 py-1.5"
        >
          <input
            value={m.path}
            onChange={(e) => update(i, { path: e.target.value })}
            placeholder="/mount/path"
            className="min-w-0 flex-1 rounded-md border border-border bg-surface-0 px-2 py-1.5 font-mono text-[12px] text-text-primary outline-none focus-visible:border-accent"
          />
          <div className="flex shrink-0 overflow-hidden rounded-md border border-border">
            {(["ro", "rw"] as MountMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => update(i, { mode })}
                className={cn(
                  "px-2.5 py-1.5 font-mono text-[11px] uppercase transition-colors",
                  m.mode === mode
                    ? "bg-accent-soft text-accent"
                    : "bg-surface-1 text-text-muted hover:text-text-secondary",
                )}
              >
                {mode}
              </button>
            ))}
          </div>
          <EffectClassTag
            effectClass={effectClassForPrefix(m.path)}
            className="w-[68px] justify-center"
          />
          <button
            onClick={() => remove(i)}
            className="grid h-7 w-7 shrink-0 place-items-center rounded-md text-text-muted transition-colors hover:bg-surface-3 hover:text-danger"
            title="Remove mount"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ))}
      <button
        onClick={add}
        className="flex items-center justify-center gap-1.5 rounded-lg border border-dashed border-border py-2 text-[12px] text-text-muted transition-colors hover:border-border-hover hover:text-text-secondary"
      >
        <Plus size={14} /> Add mount
      </button>
    </div>
  );
}
