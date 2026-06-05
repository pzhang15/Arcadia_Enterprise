import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

type Tone =
  | "neutral"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "outline";

type Size = "xs" | "sm" | "md";

interface Props extends HTMLAttributes<HTMLSpanElement> {
  tone?: Tone;
  size?: Size;
  icon?: ReactNode;
  dot?: boolean;
  mono?: boolean;
}

const TONE_STYLES: Record<Tone, string> = {
  neutral: "bg-surface-3 text-text-secondary",
  accent: "bg-accent-soft text-accent",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  info: "bg-info-soft text-info",
  outline: "border border-border bg-transparent text-text-secondary",
};

const DOT_STYLES: Record<Tone, string> = {
  neutral: "bg-text-muted",
  accent: "bg-accent",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info",
  outline: "bg-text-muted",
};

const SIZE_STYLES: Record<Size, string> = {
  xs: "px-1.5 py-0.5 text-[10px] gap-1 h-[18px] rounded",
  sm: "px-2 py-0.5 text-[11px] gap-1.5 h-5 rounded-md",
  md: "px-2.5 py-1 text-xs gap-1.5 h-6 rounded-md",
};

export function Badge({
  tone = "neutral",
  size = "sm",
  icon,
  dot,
  mono,
  className,
  children,
  ...rest
}: Props) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center font-medium leading-none",
        TONE_STYLES[tone],
        SIZE_STYLES[size],
        mono && "font-mono tabular-nums",
        className,
      )}
      {...rest}
    >
      {dot && (
        <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", DOT_STYLES[tone])} />
      )}
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </span>
  );
}
