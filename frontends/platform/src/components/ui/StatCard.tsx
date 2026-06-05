import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Tone = "default" | "success" | "warning" | "danger" | "info" | "accent";

interface Props {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ReactNode;
  tone?: Tone;
  trend?: { value: string; positive?: boolean };
  className?: string;
}

const TONE_VALUE: Record<Tone, string> = {
  default: "text-text-primary",
  success: "text-success",
  warning: "text-warning",
  danger: "text-danger",
  info: "text-info",
  accent: "text-accent",
};

const TONE_ICON: Record<Tone, string> = {
  default: "bg-surface-2 text-text-secondary",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  info: "bg-info-soft text-info",
  accent: "bg-accent-soft text-accent",
};

export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = "default",
  trend,
  className,
}: Props) {
  return (
    <div
      className={cn(
        "group relative overflow-hidden rounded-xl border border-border bg-surface-1 px-4 py-3.5 transition-colors hover:border-border-hover",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-semibold uppercase tracking-[0.08em] text-text-muted">
            {label}
          </div>
          <div
            className={cn(
              "mt-1.5 text-2xl font-semibold tabular-nums leading-none",
              TONE_VALUE[tone],
            )}
          >
            {value}
          </div>
          {hint && (
            <div className="mt-2 truncate text-[11px] text-text-muted">
              {hint}
            </div>
          )}
        </div>
        {icon && (
          <span
            className={cn(
              "grid h-9 w-9 shrink-0 place-items-center rounded-lg",
              TONE_ICON[tone],
            )}
          >
            {icon}
          </span>
        )}
      </div>
      {trend && (
        <div
          className={cn(
            "mt-2 inline-flex items-center gap-1 text-[11px] font-medium",
            trend.positive ? "text-success" : "text-danger",
          )}
        >
          {trend.positive ? "↑" : "↓"} {trend.value}
        </div>
      )}
    </div>
  );
}
