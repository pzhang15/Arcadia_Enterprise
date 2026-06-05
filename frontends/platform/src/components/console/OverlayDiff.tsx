import { FileDiff, FilePlus2, FileX2, FolderPlus, PencilLine } from "lucide-react";
import type { ReactNode } from "react";
import type { OverlayDiff as OverlayDiffData } from "@/types/console";
import { EFFECT_DEFAULT_CAPTURE } from "@/lib/captureState";
import { mountBgClass } from "@/lib/mountColor";
import { cn, formatBytes } from "@/lib/utils";
import { CaptureBadge } from "./CaptureBadge";
import { EffectClassTag } from "./EffectClassTag";

const OP_ICON: Record<string, ReactNode> = {
  write: <PencilLine size={12} />,
  append: <PencilLine size={12} />,
  truncate: <PencilLine size={12} />,
  create: <FilePlus2 size={12} />,
  mkdir: <FolderPlus size={12} />,
  rename: <FileDiff size={12} />,
  unlink: <FileX2 size={12} />,
  rmdir: <FileX2 size={12} />,
};

interface Props {
  overlay: OverlayDiffData;
  selectedPrefix?: string | null;
}

export function OverlayDiff({ overlay, selectedPrefix }: Props) {
  const mounts = overlay.mounts
    .filter((m) => (selectedPrefix ? m.prefix === selectedPrefix : true))
    .filter((m) => m.changes.length > 0);

  if (mounts.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
        <FileDiff size={22} className="text-text-faint" />
        <p className="text-[12px] text-text-muted">Overlay is clean.</p>
        <p className="max-w-[260px] text-[11px] text-text-faint">
          No captured writes against backing state. Run an agent that writes,
          then reset to return the world to pristine.
        </p>
      </div>
    );
  }

  return (
    <div className="scrollbar-thin h-full overflow-y-auto p-3">
      <div className="flex flex-col gap-3">
        {mounts.map((m) => (
          <div
            key={m.prefix}
            className="overflow-hidden rounded-lg border border-border bg-surface-1/60"
          >
            <div className="flex items-center gap-2 border-b border-border/60 bg-surface-1 px-3 py-2">
              <span className={cn("h-2 w-2 shrink-0 rounded-full", mountBgClass(m.prefix))} />
              <span className="truncate font-mono text-[12px] text-text-primary">
                {m.prefix}
              </span>
              <EffectClassTag effectClass={m.effect_class} />
              <span className="ml-auto font-mono text-[10px] text-text-faint tabular-nums">
                +{m.changes.length}
              </span>
            </div>
            <ul className="divide-y divide-border/50">
              {m.changes.map((c) => (
                <li key={c.key} className="flex items-center gap-2 px-3 py-1.5">
                  <span className="shrink-0 text-captured">
                    {OP_ICON[c.op] ?? <PencilLine size={12} />}
                  </span>
                  <span className="w-14 shrink-0 font-mono text-[10px] uppercase text-text-muted">
                    {c.op}
                  </span>
                  <span className="truncate font-mono text-[11px] text-text-secondary">
                    {c.path}
                  </span>
                  <CaptureBadge
                    state={EFFECT_DEFAULT_CAPTURE[m.effect_class]}
                    size="xs"
                    className="ml-auto"
                  />
                  <span className="w-12 shrink-0 text-right font-mono text-[10px] text-text-faint tabular-nums">
                    {formatBytes(c.bytes || 0)}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
