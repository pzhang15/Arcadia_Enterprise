import { useState } from "react";
import { Brain, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props {
  text: string;
  streaming?: boolean;
  defaultOpen?: boolean;
  accentText?: string;
}

export function ReasoningBlock({
  text,
  streaming,
  defaultOpen = true,
  accentText = "text-accent",
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const trimmed = text.trim();
  if (!trimmed && !streaming) return null;

  return (
    <div className="my-2 overflow-hidden rounded-lg border border-border bg-surface-2/40">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left transition-colors hover:bg-surface-2"
      >
        <Brain size={12} className={cn("shrink-0", accentText)} />
        <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-text-muted">
          Reasoning
        </span>
        {streaming && (
          <span className="inline-flex items-center gap-1 text-[10px] text-text-muted">
            <span className="h-1 w-1 animate-pulse rounded-full bg-accent" />
            thinking…
          </span>
        )}
        <span className="ml-auto text-text-muted">
          {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
      </button>
      {open && (
        <div className="border-t border-border bg-surface-1/50 px-3 py-2">
          <p
            className={cn(
              "whitespace-pre-wrap text-[12px] leading-relaxed italic text-text-secondary",
              streaming && "animate-pulse-fade",
            )}
          >
            {trimmed || "…"}
          </p>
        </div>
      )}
    </div>
  );
}
