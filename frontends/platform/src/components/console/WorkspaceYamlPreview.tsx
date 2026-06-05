import { useMemo } from "react";
import type { MountSpec } from "@/types/console";
import { effectClassForPrefix } from "@/lib/effectClass";

interface Props {
  name: string;
  templateId: string;
  mode: string;
  mounts: MountSpec[];
}

export function buildWorkspaceYaml({
  name,
  templateId,
  mode,
  mounts,
}: Props): string {
  const lines: string[] = [];
  lines.push(`name: ${name || "untitled"}`);
  lines.push(`template: ${templateId}`);
  lines.push(`mode: ${mode}`);
  lines.push("mounts:");
  if (mounts.length === 0) {
    lines.push("  []");
  }
  for (const m of mounts) {
    lines.push(`  - path: ${m.path || "/"}`);
    lines.push(`    mode: ${m.mode}`);
    lines.push(`    effect_class: ${effectClassForPrefix(m.path)}`);
  }
  return lines.join("\n");
}

export function WorkspaceYamlPreview(props: Props) {
  const yaml = useMemo(() => buildWorkspaceYaml(props), [props]);
  return (
    <pre className="scrollbar-thin h-full overflow-auto rounded-lg border border-border bg-surface-0 p-3 font-mono text-[11.5px] leading-relaxed text-text-secondary">
      {yaml}
    </pre>
  );
}
