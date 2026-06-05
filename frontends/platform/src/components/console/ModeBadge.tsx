import { FlaskConical, ShieldAlert } from "lucide-react";
import type { WorkspaceMode } from "@/types/console";
import { cn } from "@/lib/utils";

interface Props {
  mode: WorkspaceMode;
  size?: "sm" | "md";
  onClick?: () => void;
  className?: string;
}

export function ModeBadge({ mode, size = "md", onClick, className }: Props) {
  const isLive = mode === "LIVE";
  const Icon = isLive ? ShieldAlert : FlaskConical;
  const Tag = onClick ? "button" : "span";
  return (
    <Tag
      onClick={onClick}
      title={
        isLive
          ? "LIVE — writes pass through to real backends"
          : "TEST — all external writes are captured/simulated"
      }
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 border font-mono font-semibold uppercase leading-none tracking-wider transition-colors",
        size === "md" ? "h-6 px-2.5 text-[11px] rounded-md" : "h-5 px-2 text-[10px] rounded",
        isLive
          ? "border-live/60 bg-live-soft text-live"
          : "border-success/40 bg-success-soft text-success",
        onClick && "hover:border-border-hover",
        className,
      )}
    >
      <Icon size={12} strokeWidth={2.25} />
      {mode}
    </Tag>
  );
}
