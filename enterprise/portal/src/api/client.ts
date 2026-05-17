import type {
  Ticket,
  Employee,
  Expense,
  PurchaseOrder,
  Invoice,
  BudgetData,
  PagerDutyIncident,
  Deployment,
  CustomerAccount,
  Escalation,
  Contract,
  Audit,
  Policy,
} from "../types";

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
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
