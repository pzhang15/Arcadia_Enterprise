import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/utils";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  interactive?: boolean;
  elevated?: boolean;
}

export function Card({
  interactive,
  elevated,
  className,
  children,
  ...rest
}: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-surface-1",
        elevated && "shadow-md",
        interactive &&
          "transition-all duration-150 ease-out hover:border-border-hover hover:bg-surface-2 cursor-pointer",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

interface CardHeaderProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  icon?: ReactNode;
}

export function CardHeader({
  title,
  subtitle,
  actions,
  icon,
  className,
  children,
  ...rest
}: CardHeaderProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-3 border-b border-border px-5 py-3.5",
        className,
      )}
      {...rest}
    >
      {icon && (
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-surface-2 text-text-secondary">
          {icon}
        </span>
      )}
      {(title || subtitle) && (
        <div className="min-w-0 flex-1">
          {title && (
            <div className="truncate text-[13px] font-semibold text-text-primary">
              {title}
            </div>
          )}
          {subtitle && (
            <div className="truncate text-xs text-text-muted">{subtitle}</div>
          )}
        </div>
      )}
      {children}
      {actions && <div className="ml-auto flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function CardBody({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("px-5 py-4", className)} {...rest}>
      {children}
    </div>
  );
}
