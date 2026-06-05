import type { EffectClass } from "@/types/console";

const BY_PREFIX: Record<string, EffectClass> = {
  slack: "external-effect",
  linear: "external-effect",
  gmail: "external-effect",
  email: "external-effect",
  github: "external-effect",
  pagerduty: "external-effect",
  discord: "external-effect",
  telegram: "external-effect",
  trello: "external-effect",
  postgres: "system-of-record",
  mongodb: "system-of-record",
  customers: "system-of-record",
  finance: "system-of-record",
  datadog: "durable-internal",
  s3: "durable-internal",
  tickets: "durable-internal",
  compliance: "durable-internal",
  sheets: "durable-internal",
  gdocs: "durable-internal",
  gdrive: "durable-internal",
  notion: "durable-internal",
  hr: "durable-internal",
  scratch: "scratch",
  tmp: "scratch",
};

export function effectClassForPrefix(prefix: string): EffectClass {
  const head = prefix.replace(/^\/+/, "").split("/")[0].toLowerCase();
  if (!head) return "scratch";
  return BY_PREFIX[head] ?? "durable-internal";
}
