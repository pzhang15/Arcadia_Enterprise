import { FlaskConical, Layers, Zap } from "lucide-react";
import type { ReactNode } from "react";
import type { CaptureState } from "@/types/console";
import { CAPTURE_META } from "@/lib/captureState";
import { cn } from "@/lib/utils";

const ICONS: Record<CaptureState, ReactNode> = {
  captured: <Layers size={11} strokeWidth={2.25} />,
  simulated: <FlaskConical size={11} strokeWidth={2.25} />,
  live: <Zap size={11} strokeWidth={2.25} />,
};

type Size = "xs" | "sm" | "md";

const SIZE_STYLES: Record<Size, string> = {
  xs: "h-[18px] px-1.5 text-[9px] gap-1 rounded",
  sm: "h-5 px-2 text-[10px] gap-1.5 rounded-md",
  md: "h-6 px-2.5 text-[11px] gap-1.5 rounded-md",
};

interface Props {
  state: CaptureState;
  size?: Size;
  iconOnly?: boolean;
  flash?: boolean;
  className?: string;
}

export function CaptureBadge({
  state,
  size = "sm",
  iconOnly,
  flash,
  className,
}: Props) {
  const meta = CAPTURE_META[state];
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center border font-mono font-semibold uppercase leading-none tracking-wider",
        meta.bg,
        meta.text,
        meta.border,
        SIZE_STYLES[size],
        flash && state === "live" && "animate-promote-flash",
        flash && state !== "live" && "animate-capture-flash",
        iconOnly && "px-0 justify-center aspect-square",
        className,
      )}
      title={`${meta.label} — ${captionFor(state)}`}
    >
      {ICONS[state]}
      {!iconOnly && meta.label}
    </span>
  );
}

function captionFor(state: CaptureState): string {
  if (state === "captured") return "in overlay, reversible";
  if (state === "simulated") return "side-effect faked, not sent";
  return "committed to the real world, irreversible";
}
