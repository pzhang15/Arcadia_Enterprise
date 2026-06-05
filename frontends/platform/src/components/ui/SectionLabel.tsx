import type { HTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function SectionLabel({
  className,
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "text-[10px] font-semibold uppercase tracking-[0.1em] text-text-muted",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
