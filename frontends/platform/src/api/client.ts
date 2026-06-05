import type { AGUIEvent } from "../types/agui";
import type {
  ConsoleWorkspaceBrief,
  ConsoleWorkspaceDetail,
  DryRunResult,
  MountSpec,
  OverlayDiff,
  PendingEffect,
  PromoteResult,
  SnapshotEntry,
  TestRunResult,
  TrajectoryEntry,
  WorkspaceMode,
} from "../types/console";
import type {
  AggregateReport,
  Audit,
  BudgetData,
  Contract,
  CustomerAccount,
  Deployment,
  Employee,
  Escalation,
  Expense,
  Invoice,
  PagerDutyIncident,
  Policy,
  PurchaseOrder,
  ScoreCard,
  SweepInfo,
  Ticket,
  TraceDetail,
  TraceSummary,
} from "../types";
import type { InvestigationMeta } from "../types/investigation";
import type { ReplayResponse } from "../types/replay";

const BASE = "";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export async function listInvestigations(): Promise<InvestigationMeta[]> {
  return fetchJson<InvestigationMeta[]>("/api/investigations");
}

export async function getInvestigationApi(
  sessionId: string,
): Promise<InvestigationMeta> {
  return fetchJson<InvestigationMeta>(`/api/investigations/${sessionId}`);
}

export async function upsertInvestigationApi(
  meta: InvestigationMeta,
): Promise<InvestigationMeta> {
  return postJson<InvestigationMeta>("/api/investigations", meta);
}

export async function patchInvestigationApi(
  sessionId: string,
  fields: Partial<InvestigationMeta>,
): Promise<InvestigationMeta> {
  return patchJson<InvestigationMeta>(`/api/investigations/${sessionId}`, fields);
}

export async function deleteInvestigationApi(sessionId: string): Promise<void> {
  await fetch(`${BASE}/api/investigations/${sessionId}`, { method: "DELETE" });
}

export async function listSweeps(): Promise<SweepInfo[]> {
  return fetchJson<SweepInfo[]>("/api/results");
}

export async function getAggregate(
  scenario: string,
  sweepId: string,
): Promise<AggregateReport> {
  return fetchJson<AggregateReport>(
    `/api/results/${scenario}/${encodeURIComponent(sweepId)}`,
  );
}

export async function getScorecard(
  scenario: string,
  sweepId: string,
  runId: string,
): Promise<ScoreCard> {
  return fetchJson<ScoreCard>(
    `/api/results/${scenario}/${encodeURIComponent(sweepId)}/runs/${encodeURIComponent(runId)}`,
  );
}

export async function listTraces(
  limit = 50,
  offset = 0,
): Promise<TraceSummary[]> {
  return fetchJson<TraceSummary[]>(
    `/api/traces?limit=${limit}&offset=${offset}`,
  );
}

export async function getTrace(traceId: string): Promise<TraceDetail> {
  return fetchJson<TraceDetail>(`/api/traces/${encodeURIComponent(traceId)}`);
}

export async function getReplay(
  sessionId: string,
  cursor?: number,
  runId?: string,
): Promise<ReplayResponse> {
  const params = new URLSearchParams();
  if (cursor !== undefined) params.set("cursor", String(cursor));
  if (runId !== undefined) params.set("run_id", runId);
  const qs = params.toString();
  return fetchJson<ReplayResponse>(
    `/api/sessions/${encodeURIComponent(sessionId)}/replay${
      qs ? `?${qs}` : ""
    }`,
  );
}

export async function getTraceStats(): Promise<{
  total_traces: number;
  total_spans: number;
  by_level?: Record<string, number>;
}> {
  return fetchJson(`/api/traces/stats/summary`);
}

export function fetchTickets(queue: string): Promise<Ticket[]> {
  return fetchJson(`/api/tickets/${queue}`);
}

export function fetchTicket(queue: string, ticketId: string): Promise<Ticket> {
  return fetchJson(`/api/tickets/${queue}/${ticketId}`);
}

export function fetchEmployees(): Promise<Employee[]> {
  return fetchJson("/api/employees");
}

export function fetchSheet(sheetId: string): Promise<Record<string, unknown>> {
  return fetchJson(`/api/sheets/${sheetId}`);
}

export function fetchExpenses(): Promise<Expense[]> {
  return fetchJson("/api/finance/expenses");
}

export function fetchPurchaseOrders(): Promise<PurchaseOrder[]> {
  return fetchJson("/api/finance/purchase-orders");
}

export function fetchInvoices(): Promise<Invoice[]> {
  return fetchJson("/api/finance/invoices");
}

export function fetchBudgets(): Promise<BudgetData> {
  return fetchJson("/api/finance/budgets");
}

export function fetchIncidents(): Promise<PagerDutyIncident[]> {
  return fetchJson("/api/engineering/incidents");
}

export function fetchDeployments(): Promise<Deployment[]> {
  return fetchJson("/api/engineering/deployments");
}

export function fetchMetrics(): Promise<Record<string, unknown>> {
  return fetchJson("/api/engineering/metrics");
}

export function fetchAccounts(): Promise<CustomerAccount[]> {
  return fetchJson("/api/customers/accounts");
}

export function fetchEscalations(): Promise<Escalation[]> {
  return fetchJson("/api/customers/escalations");
}

export function fetchContracts(): Promise<Contract[]> {
  return fetchJson("/api/compliance/contracts");
}

export function fetchAudits(): Promise<Audit[]> {
  return fetchJson("/api/compliance/audits");
}

export function fetchPolicies(): Promise<Policy[]> {
  return fetchJson("/api/compliance/policies");
}

export async function createSession(
  services: string[],
): Promise<{ id: string; status: string; has_workspace: boolean }> {
  return postJson("/api/sessions", { services });
}

export async function sendMessage(
  sessionId: string,
  message: string,
): Promise<{ reply: string; status: string }> {
  return postJson(`/api/sessions/${sessionId}/message`, { message });
}

export async function getSessionStatus(id: string) {
  return fetchJson<{
    id: string;
    status: string;
    message_count: number;
  }>(`/api/sessions/${id}/status`);
}

export async function getSessionHistory(id: string) {
  return fetchJson<
    { role: string; content: string; timestamp: number }[]
  >(`/api/sessions/${id}/history`);
}

export async function getSessionTrace(id: string) {
  return fetchJson<{
    session_id: string;
    events: AGUIEvent[];
    event_count: number;
  }>(`/api/sessions/${id}/trace`);
}

export async function listSessions() {
  return fetchJson<
    {
      id: string;
      status: string;
      services: string[];
      created_at: number;
      message_count: number;
      last_message: string;
    }[]
  >("/api/sessions");
}

export async function getQuickActions() {
  return fetchJson<
    { id: string; label: string; services: string[]; task: string }[]
  >("/api/quick-actions");
}

export async function getConfig() {
  return fetchJson<{ has_api_key: boolean; model: string }>("/api/config");
}

export async function vfsList(
  sessionId: string,
  path: string = "/",
): Promise<{
  entries: { name: string; type: "dir" | "file"; size?: number }[];
}> {
  return fetchJson(`/api/sessions/${sessionId}/vfs?path=${encodeURIComponent(path)}`);
}

export async function vfsFile(
  sessionId: string,
  path: string,
): Promise<{ content: string; size: number; path: string }> {
  return fetchJson(
    `/api/sessions/${sessionId}/vfs/file?path=${encodeURIComponent(path)}`,
  );
}

// ── Console: Workspaces (dev dog-food loop) ──────────────────────────────

async function deleteJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

const CONSOLE = "/api/console/workspaces";

export async function listConsoleWorkspaces(): Promise<ConsoleWorkspaceBrief[]> {
  return fetchJson<ConsoleWorkspaceBrief[]>(CONSOLE);
}

export async function createConsoleWorkspace(input: {
  name: string;
  template_id: string;
  mounts: MountSpec[];
}): Promise<ConsoleWorkspaceDetail> {
  return postJson<ConsoleWorkspaceDetail>(CONSOLE, input);
}

export async function getConsoleWorkspace(
  id: string,
): Promise<ConsoleWorkspaceDetail> {
  return fetchJson<ConsoleWorkspaceDetail>(`${CONSOLE}/${id}`);
}

export async function deleteConsoleWorkspace(
  id: string,
): Promise<{ id: string; closed_at: number }> {
  return deleteJson(`${CONSOLE}/${id}`);
}

export async function standupDryRun(id: string): Promise<DryRunResult> {
  return postJson<DryRunResult>(`${CONSOLE}/${id}/standup/dryrun`, {});
}

export async function standupWorkspace(
  id: string,
): Promise<ConsoleWorkspaceDetail> {
  return postJson<ConsoleWorkspaceDetail>(`${CONSOLE}/${id}/standup`, {});
}

export async function branchWorkspace(
  id: string,
  branch?: string,
): Promise<ConsoleWorkspaceDetail> {
  return postJson<ConsoleWorkspaceDetail>(`${CONSOLE}/${id}/branch`, {
    branch,
  });
}

export async function snapshotWorkspace(
  id: string,
  name?: string,
): Promise<SnapshotEntry> {
  return postJson<SnapshotEntry>(`${CONSOLE}/${id}/snapshot`, { name });
}

export async function resetWorkspace(
  id: string,
): Promise<ConsoleWorkspaceDetail> {
  return postJson<ConsoleWorkspaceDetail>(`${CONSOLE}/${id}/reset`, {});
}

export async function getOverlay(id: string): Promise<OverlayDiff> {
  return fetchJson<OverlayDiff>(`${CONSOLE}/${id}/overlay`);
}

export async function getEffects(
  id: string,
): Promise<{ effects: PendingEffect[] }> {
  return fetchJson<{ effects: PendingEffect[] }>(`${CONSOLE}/${id}/effects`);
}

export async function getTrajectory(
  id: string,
): Promise<{ entries: TrajectoryEntry[] }> {
  return fetchJson<{ entries: TrajectoryEntry[] }>(`${CONSOLE}/${id}/trajectory`);
}

export async function promoteEffects(
  id: string,
  keys: string[],
): Promise<PromoteResult> {
  return postJson<PromoteResult>(`${CONSOLE}/${id}/promote`, { keys });
}

export async function setWorkspaceMode(
  id: string,
  mode: WorkspaceMode,
): Promise<ConsoleWorkspaceDetail> {
  return postJson<ConsoleWorkspaceDetail>(`${CONSOLE}/${id}/mode`, { mode });
}

export async function getConsoleFile(
  id: string,
  path: string,
): Promise<{ content: string; size: number; path: string }> {
  return fetchJson(`${CONSOLE}/${id}/file?path=${encodeURIComponent(path)}`);
}

export async function createConsoleSession(
  id: string,
): Promise<{ id: string; workspace_id: string; status: string }> {
  return postJson(`${CONSOLE}/${id}/session`, {});
}

export async function testRunWorkspace(
  id: string,
  commands?: string[],
): Promise<TestRunResult> {
  return postJson<TestRunResult>(
    `${CONSOLE}/${id}/test-run`,
    commands ? { commands } : {},
  );
}
