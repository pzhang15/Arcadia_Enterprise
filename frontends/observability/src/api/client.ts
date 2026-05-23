import type {
  AggregateReport,
  ScoreCard,
  SweepInfo,
  TraceDetail,
  TraceSummary,
} from "../types";

const BASE = "/api";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export async function listSweeps(): Promise<SweepInfo[]> {
  return fetchJson<SweepInfo[]>("/results");
}

export async function getAggregate(
  scenario: string,
  sweepId: string,
): Promise<AggregateReport> {
  return fetchJson<AggregateReport>(
    `/results/${scenario}/${encodeURIComponent(sweepId)}`,
  );
}

export async function getScorecard(
  scenario: string,
  sweepId: string,
  runId: string,
): Promise<ScoreCard> {
  return fetchJson<ScoreCard>(
    `/results/${scenario}/${encodeURIComponent(sweepId)}/runs/${encodeURIComponent(runId)}`,
  );
}

export async function listTraces(
  limit = 50,
  offset = 0,
): Promise<TraceSummary[]> {
  return fetchJson<TraceSummary[]>(
    `/traces?limit=${limit}&offset=${offset}`,
  );
}

export async function getTrace(traceId: string): Promise<TraceDetail> {
  return fetchJson<TraceDetail>(`/traces/${encodeURIComponent(traceId)}`);
}

export async function getTraceStats(): Promise<{
  total_traces: number;
  total_spans: number;
  by_level?: Record<string, number>;
}> {
  return fetchJson(`/traces/stats/summary`);
}
