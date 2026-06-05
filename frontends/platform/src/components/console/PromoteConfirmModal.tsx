import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, FlaskConical, X } from "lucide-react";
import type { EffectClass, PendingEffect } from "@/types/console";
import { EFFECT_META } from "@/lib/captureState";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui";

const CONFIRM_PHRASE = "PROMOTE";

const ACTION_VERB: Record<EffectClass, (n: number) => string> = {
  "external-effect": (n) => `send ${n} external effect${n === 1 ? "" : "s"}`,
  "system-of-record": (n) => `write ${n} system-of-record change${n === 1 ? "" : "s"}`,
  "durable-internal": (n) => `apply ${n} durable write${n === 1 ? "" : "s"}`,
  scratch: (n) => `flush ${n} scratch write${n === 1 ? "" : "s"}`,
};

interface Props {
  open: boolean;
  effects: PendingEffect[];
  onConfirm: () => void;
  onCancel: () => void;
  committing?: boolean;
}

export function PromoteConfirmModal({
  open,
  effects,
  onConfirm,
  onCancel,
  committing,
}: Props) {
  const [typed, setTyped] = useState("");

  useEffect(() => {
    if (open) setTyped("");
  }, [open]);

  const byClass = useMemo(() => {
    const m = new Map<EffectClass, number>();
    for (const e of effects) m.set(e.effect_class, (m.get(e.effect_class) ?? 0) + 1);
    return m;
  }, [effects]);

  const requiresTyped = byClass.has("external-effect");
  const canConfirm =
    effects.length > 0 &&
    !committing &&
    (!requiresTyped || typed.trim().toUpperCase() === CONFIRM_PHRASE);

  if (!open) return null;

  const sentence = [...byClass.entries()]
    .map(([cls, n]) => ACTION_VERB[cls](n))
    .join(", ");

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onCancel}
    >
      <div
        className="w-full max-w-lg overflow-hidden rounded-xl border border-live/40 bg-surface-1 shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2.5 border-b border-border px-4 py-3">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-live-soft text-live">
            <AlertTriangle size={15} />
          </span>
          <div className="min-w-0">
            <h2 className="text-[13px] font-semibold text-text-primary">
              Promote {effects.length} effect{effects.length === 1 ? "" : "s"} to the real world
            </h2>
            <p className="text-[11px] text-text-muted">
              This is the only path from captured to real.
            </p>
          </div>
          <button
            onClick={onCancel}
            className="ml-auto grid h-7 w-7 place-items-center rounded-md text-text-muted hover:bg-surface-3 hover:text-text-primary"
          >
            <X size={15} />
          </button>
        </div>

        <div className="space-y-3 px-4 py-3.5">
          <p className="text-[13px] leading-relaxed text-text-secondary">
            On commit this will <span className="font-semibold text-text-primary">{sentence}</span>.
          </p>

          {byClass.has("external-effect") && (
            <div className="flex items-start gap-2 rounded-lg border border-live/40 bg-live-soft px-3 py-2">
              <AlertTriangle size={14} className="mt-0.5 shrink-0 text-live" />
              <p className="text-[12px] leading-snug text-text-secondary">
                External effects are <span className="font-semibold text-live">irreversible</span>{" "}
                once sent — they cannot be unsent.
              </p>
            </div>
          )}

          <div className="flex items-start gap-2 rounded-lg border border-simulated/40 bg-simulated-soft px-3 py-2">
            <FlaskConical size={14} className="mt-0.5 shrink-0 text-simulated" />
            <p className="text-[12px] leading-snug text-text-secondary">
              <span className="font-semibold text-simulated">Simulated commit.</span>{" "}
              The engine has no write-back primitive yet — these effects are marked
              promoted and logged, but <span className="font-semibold">no real external
              calls are made</span>.
            </p>
          </div>

          {requiresTyped && (
            <div>
              <label className="mb-1 block text-[11px] text-text-muted">
                Type <span className="font-mono font-semibold text-text-secondary">{CONFIRM_PHRASE}</span> to confirm
              </label>
              <input
                autoFocus
                value={typed}
                onChange={(e) => setTyped(e.target.value)}
                placeholder={CONFIRM_PHRASE}
                className={cn(
                  "w-full rounded-lg border bg-surface-0 px-3 py-2 font-mono text-[13px] text-text-primary outline-none",
                  typed && typed.trim().toUpperCase() !== CONFIRM_PHRASE
                    ? "border-live/50"
                    : "border-border",
                )}
              />
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-border px-4 py-3">
          <Button variant="ghost" onClick={onCancel} disabled={committing}>
            Cancel
          </Button>
          <button
            onClick={onConfirm}
            disabled={!canConfirm}
            className={cn(
              "inline-flex h-9 items-center gap-1.5 rounded-lg px-3.5 text-[13px] font-medium transition-colors",
              canConfirm
                ? "bg-live text-white hover:bg-live-strong"
                : "cursor-not-allowed bg-surface-3 text-text-faint",
            )}
          >
            {committing ? "Committing…" : `Promote ${effects.length}`}
          </button>
        </div>
      </div>
    </div>
  );
}
