import type { RunStep } from "@/types/agui";
import type { StreamEvent } from "@/types";

export interface StepEventBuckets {
  byStep: Map<string, StreamEvent[]>;
  orphans: StreamEvent[];
}

function getEventTimeMs(e: StreamEvent): number {
  return e.timestamp > 1e12 ? e.timestamp : e.timestamp * 1000;
}

export function correlateEventsToSteps(
  events: StreamEvent[],
  steps: RunStep[],
  sessionId: string | null,
): StepEventBuckets {
  const byStep = new Map<string, StreamEvent[]>();
  const orphans: StreamEvent[] = [];
  if (steps.length === 0) {
    return { byStep, orphans: events };
  }

  const sorted = steps
    .slice()
    .sort((a, b) => a.started_at - b.started_at);

  for (const e of events) {
    if (sessionId && (e as { session?: string }).session && (e as { session?: string }).session !== sessionId) {
      continue;
    }
    const t = getEventTimeMs(e);
    let assigned: RunStep | null = null;
    for (const step of sorted) {
      const end = step.ended_at ?? Number.POSITIVE_INFINITY;
      if (t >= step.started_at && t <= end) {
        assigned = step;
      }
    }
    if (!assigned) {
      orphans.push(e);
      continue;
    }
    const arr = byStep.get(assigned.id) || [];
    arr.push(e);
    byStep.set(assigned.id, arr);
  }
  return { byStep, orphans };
}
