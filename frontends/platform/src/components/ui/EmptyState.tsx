import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface Props {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
  size?: "sm" | "md" | "lg";
}

const SIZE_PAD: Record<NonNullable<Props["size"]>, string> = {
  sm: "py-10",
  md: "py-16",
  lg: "py-24",
};

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
  size = "md",
}: Props) {
  return (
    <div
      className={cn(
        "mx-auto flex max-w-md flex-col items-center justify-center gap-3 px-6 text-center",
        SIZE_PAD[size],
        className,
      )}
    >
      {icon && (
        <div className="relative mb-1 grid h-14 w-14 place-items-center">
          <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-accent-soft to-info-soft opacity-70 blur-md" />
          <div className="relative grid h-14 w-14 place-items-center rounded-2xl border border-border bg-surface-1 text-accent">
            {icon}
          </div>
        </div>
      )}
      <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
      {description && (
        <p className="max-w-sm text-[13px] leading-relaxed text-text-muted">
          {description}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
