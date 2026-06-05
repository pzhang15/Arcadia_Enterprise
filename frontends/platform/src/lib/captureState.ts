import type { CaptureState, EffectClass } from "@/types/console";

export interface CaptureMeta {
  label: string;
  text: string;
  bg: string;
  border: string;
  dot: string;
  ring: string;
}

export const CAPTURE_META: Record<CaptureState, CaptureMeta> = {
  captured: {
    label: "CAPTURED",
    text: "text-captured",
    bg: "bg-captured-soft",
    border: "border-captured/40",
    dot: "bg-captured",
    ring: "ring-captured/40",
  },
  simulated: {
    label: "SIMULATED",
    text: "text-simulated",
    bg: "bg-simulated-soft",
    border: "border-simulated/40",
    dot: "bg-simulated",
    ring: "ring-simulated/40",
  },
  live: {
    label: "LIVE",
    text: "text-live",
    bg: "bg-live-soft",
    border: "border-live/50",
    dot: "bg-live",
    ring: "ring-live/50",
  },
};

export const EFFECT_DEFAULT_CAPTURE: Record<EffectClass, CaptureState> = {
  scratch: "captured",
  "durable-internal": "captured",
  "system-of-record": "captured",
  "external-effect": "simulated",
};

export const EFFECT_META: Record<
  EffectClass,
  { label: string; short: string; text: string; bg: string }
> = {
  scratch: {
    label: "Scratch",
    short: "scratch",
    text: "text-text-muted",
    bg: "bg-surface-3",
  },
  "durable-internal": {
    label: "Durable internal",
    short: "durable",
    text: "text-captured",
    bg: "bg-captured-soft",
  },
  "system-of-record": {
    label: "System of record",
    short: "record",
    text: "text-info",
    bg: "bg-info-soft",
  },
  "external-effect": {
    label: "External effect",
    short: "external",
    text: "text-simulated",
    bg: "bg-simulated-soft",
  },
};
