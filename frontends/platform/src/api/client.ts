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
