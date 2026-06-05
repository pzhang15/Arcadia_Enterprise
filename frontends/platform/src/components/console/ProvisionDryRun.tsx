import { Check, Database, HardDrive, X } from "lucide-react";
import type { DryRunResult } from "@/types/console";
import { mountBgClass } from "@/lib/mountColor";
import { cn, formatBytes } from "@/lib/utils";
import { EffectClassTag } from "./EffectClassTag";

interface Props {
  result: DryRunResult;
}

export function ProvisionDryRun({ result }: Props) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 text-[12px] text-text-secondary">
        <Database size={14} className="text-text-muted" />
        Provision dry-run — projected backends, nothing connected yet.
      </div>

      <div className="overflow-hidden rounded-lg border border-border">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="border-b border-border bg-surface-1 text-left text-[10px] uppercase tracking-wide text-text-muted">
              <th className="px-3 py-2 font-medium">Mount</th>
              <th className="px-2 py-2 font-medium">Mode</th>
              <th className="px-2 py-2 font-medium">Effect</th>
              <th className="px-2 py-2 text-right font-medium">Files</th>
              <th className="px-3 py-2 text-right font-medium">Bytes</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {result.mounts.map((m) => (
              <tr key={m.path} className="bg-surface-0">
                <td className="px-3 py-2">
                  <span className="flex items-center gap-2">
                    <span className={cn("h-2 w-2 shrink-0 rounded-full", mountBgClass(m.path))} />
                    <span className="font-mono text-text-primary">{m.path}</span>
                    {m.exists ? (
                      <Check size={12} className="text-success" />
                    ) : (
                      <X size={12} className="text-warning" />
                    )}
                  </span>
                </td>
                <td className="px-2 py-2 font-mono text-[11px] uppercase text-text-muted">
                  {m.mode}
                </td>
                <td className="px-2 py-2">
                  <EffectClassTag effectClass={m.effect_class} />
                </td>
                <td className="px-2 py-2 text-right font-mono text-text-secondary tabular-nums">
                  {m.files}
                </td>
                <td className="px-3 py-2 text-right font-mono text-text-secondary tabular-nums">
                  {formatBytes(m.bytes)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-4 rounded-lg border border-border bg-surface-1 px-3 py-2.5">
        <span className="flex items-center gap-1.5 text-[12px] text-text-secondary">
          <HardDrive size={14} className="text-text-muted" />
          <span className="font-mono font-medium text-text-primary tabular-nums">
            {formatBytes(result.estimated_snapshot_bytes)}
          </span>
          to snapshot
        </span>
        <span className="font-mono text-[12px] text-text-muted tabular-nums">
          {result.estimated_files} files
        </span>
        <span className="ml-auto text-right text-[11px] text-text-faint">
          {result.cache_plan}
        </span>
      </div>
    </div>
  );
}
