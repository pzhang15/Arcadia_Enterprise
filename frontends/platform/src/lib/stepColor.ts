const STEP_PALETTE: { name: string; bg: string; border: string; soft: string; text: string; rail: string }[] = [
  {
    name: "violet",
    bg: "bg-mount-slack",
    border: "border-mount-slack",
    soft: "bg-mount-slack/15",
    text: "text-mount-slack",
    rail: "bg-mount-slack",
  },
  {
    name: "blue",
    bg: "bg-mount-tickets",
    border: "border-mount-tickets",
    soft: "bg-mount-tickets/15",
    text: "text-mount-tickets",
    rail: "bg-mount-tickets",
  },
  {
    name: "teal",
    bg: "bg-mount-customers",
    border: "border-mount-customers",
    soft: "bg-mount-customers/15",
    text: "text-mount-customers",
    rail: "bg-mount-customers",
  },
  {
    name: "green",
    bg: "bg-mount-pagerduty",
    border: "border-mount-pagerduty",
    soft: "bg-mount-pagerduty/15",
    text: "text-mount-pagerduty",
    rail: "bg-mount-pagerduty",
  },
  {
    name: "amber",
    bg: "bg-mount-finance",
    border: "border-mount-finance",
    soft: "bg-mount-finance/15",
    text: "text-mount-finance",
    rail: "bg-mount-finance",
  },
  {
    name: "orange",
    bg: "bg-mount-datadog",
    border: "border-mount-datadog",
    soft: "bg-mount-datadog/15",
    text: "text-mount-datadog",
    rail: "bg-mount-datadog",
  },
];

export type StepColor = (typeof STEP_PALETTE)[number];

export function stepColor(stepId: string): StepColor {
  let hash = 0;
  for (let i = 0; i < stepId.length; i++) {
    hash = (hash * 31 + stepId.charCodeAt(i)) | 0;
  }
  const idx = Math.abs(hash) % STEP_PALETTE.length;
  return STEP_PALETTE[idx];
}

export function stepColorByIndex(idx: number): StepColor {
  return STEP_PALETTE[idx % STEP_PALETTE.length];
}
