import type { EffectClass } from "@/types/console";
import { EFFECT_META } from "@/lib/captureState";
import { cn } from "@/lib/utils";

interface Props {
  effectClass: EffectClass;
  full?: boolean;
  className?: string;
}

export function EffectClassTag({ effectClass, full, className }: Props) {
  const meta = EFFECT_META[effectClass];
  return (
    <span
      className={cn(
        "inline-flex h-[18px] shrink-0 items-center rounded px-1.5 font-mono text-[10px] font-medium",
        meta.bg,
        meta.text,
        className,
      )}
      title={`Effect class: ${meta.label}`}
    >
      {full ? meta.label : meta.short}
    </span>
  );
}
