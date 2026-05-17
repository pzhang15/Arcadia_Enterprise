import type { AggregateReport, ScoreCard, SweepInfo } from "../types";

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
