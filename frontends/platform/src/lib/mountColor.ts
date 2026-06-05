const MOUNT_TEXT: Record<string, string> = {
  tickets: "text-mount-tickets",
  slack: "text-mount-slack",
  github: "text-mount-github",
  pagerduty: "text-mount-pagerduty",
  finance: "text-mount-finance",
  datadog: "text-mount-datadog",
  compliance: "text-mount-compliance",
  customers: "text-mount-customers",
};

const MOUNT_BG: Record<string, string> = {
  tickets: "bg-mount-tickets",
  slack: "bg-mount-slack",
  github: "bg-mount-github",
  pagerduty: "bg-mount-pagerduty",
  finance: "bg-mount-finance",
  datadog: "bg-mount-datadog",
  compliance: "bg-mount-compliance",
  customers: "bg-mount-customers",
};

export function mountKey(prefix: string): string {
  return prefix.replace(/^\//, "").split("/")[0].toLowerCase() || "root";
}

export function mountTextClass(prefix: string): string {
  return MOUNT_TEXT[mountKey(prefix)] ?? "text-text-secondary";
}

export function mountBgClass(prefix: string): string {
  return MOUNT_BG[mountKey(prefix)] ?? "bg-text-faint";
}
