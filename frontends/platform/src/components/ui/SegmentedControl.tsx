import { cn } from "@/lib/utils";

interface SegmentOption<T extends string> {
  id: T;
  label: string;
  count?: number;
}

interface Props<T extends string> {
  value: T;
  options: SegmentOption<T>[];
  onChange: (id: T) => void;
  className?: string;
  size?: "sm" | "md";
}

export function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
  className,
  size = "md",
}: Props<T>) {
  const padding = size === "sm" ? "px-2.5 py-1 text-[11px]" : "px-3 py-1.5 text-xs";
  return (
    <div
      className={cn(
        "inline-flex items-center gap-0.5 rounded-lg border border-border bg-surface-2 p-0.5",
        className,
      )}
    >
      {options.map((opt) => {
        const active = opt.id === value;
        return (
          <button
            key={opt.id}
            onClick={() => onChange(opt.id)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md font-medium transition-all duration-150",
              padding,
              active
                ? "bg-surface-4 text-text-primary shadow-xs"
                : "text-text-muted hover:text-text-secondary",
            )}
          >
            {opt.label}
            {opt.count !== undefined && (
              <span
                className={cn(
                  "rounded px-1 py-px text-[10px] font-semibold tabular-nums",
                  active
                    ? "bg-surface-2 text-text-secondary"
                    : "bg-surface-3 text-text-muted",
                )}
              >
                {opt.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
