import { describe, expect, it } from "vitest";
import {
  createSession,
  fetchAccounts,
  fetchAudits,
  fetchBudgets,
  fetchContracts,
  fetchDeployments,
  fetchEmployees,
  fetchEscalations,
  fetchExpenses,
  fetchIncidents,
  fetchInvoices,
  fetchPolicies,
  fetchPurchaseOrders,
  fetchTickets,
  getConfig,
  getQuickActions,
  getSessionHistory,
  getTrace,
  getTraceStats,
  listSessions,
  listSweeps,
  listTraces,
  sendMessage,
} from "../client";
import { http, HttpResponse } from "msw";
import { server } from "../../test/mocks/server";
import { TICKETS, EXPENSES, EMPLOYEES } from "../../test/fixtures";

describe("fetchJson error handling", () => {
  it("throws on non-200 response", async () => {
    server.use(
      http.get("/api/tickets/:queue", () => new HttpResponse(null, { status: 500, statusText: "Internal Server Error" })),
    );
    await expect(fetchTickets("it-helpdesk")).rejects.toThrow("500");
  });

  it("throws on 404", async () => {
    server.use(
      http.get("/api/employees", () => new HttpResponse(null, { status: 404, statusText: "Not Found" })),
    );
    await expect(fetchEmployees()).rejects.toThrow("404");
  });
});

describe("portal endpoints", () => {
  it("fetchTickets calls correct path", async () => {
    const result = await fetchTickets("it-helpdesk");
    expect(result).toHaveLength(TICKETS.length);
    expect(result[0].ticket_id).toBe("INC-1001");
  });

  it("fetchExpenses returns expenses", async () => {
    const result = await fetchExpenses();
    expect(result).toHaveLength(EXPENSES.length);
  });

  it("fetchPurchaseOrders returns POs", async () => {
    const result = await fetchPurchaseOrders();
    expect(result.length).toBeGreaterThan(0);
  });

  it("fetchInvoices returns array", async () => {
    const result = await fetchInvoices();
    expect(Array.isArray(result)).toBe(true);
  });

  it("fetchBudgets returns departments", async () => {
    const result = await fetchBudgets();
    expect(result.departments).toBeDefined();
    expect(result.departments.length).toBeGreaterThan(0);
  });

  it("fetchIncidents returns incidents", async () => {
    const result = await fetchIncidents();
    expect(result.length).toBeGreaterThan(0);
  });

  it("fetchDeployments returns deployments", async () => {
    const result = await fetchDeployments();
    expect(result.length).toBeGreaterThan(0);
  });

  it("fetchEmployees returns employees", async () => {
    const result = await fetchEmployees();
    expect(result).toHaveLength(EMPLOYEES.length);
  });

  it("fetchAccounts returns accounts", async () => {
    const result = await fetchAccounts();
    expect(result.length).toBeGreaterThan(0);
  });

  it("fetchEscalations returns escalations", async () => {
    const result = await fetchEscalations();
    expect(result.length).toBeGreaterThan(0);
  });

  it("fetchContracts returns contracts", async () => {
    const result = await fetchContracts();
    expect(result.length).toBeGreaterThan(0);
  });

  it("fetchAudits returns audits", async () => {
    const result = await fetchAudits();
    expect(result.length).toBeGreaterThan(0);
  });

  it("fetchPolicies returns policies", async () => {
    const result = await fetchPolicies();
    expect(result.length).toBeGreaterThan(0);
  });
});

describe("session endpoints", () => {
  it("createSession posts services", async () => {
    const result = await createSession(["it", "finance"]);
    expect(result.id).toBeDefined();
    expect(result.has_workspace).toBe(true);
  });

  it("sendMessage posts and returns reply", async () => {
    const result = await sendMessage("abc123", "List tickets");
    expect(result.reply).toBe("Here are the results.");
    expect(result.status).toBe("ready");
  });

  it("getSessionHistory returns entries", async () => {
    const result = await getSessionHistory("abc123");
    expect(result.length).toBe(2);
    expect(result[0].role).toBe("user");
  });

  it("listSessions returns session list", async () => {
    const result = await listSessions();
    expect(result.length).toBeGreaterThan(0);
  });

  it("postJson throws on error", async () => {
    server.use(
      http.post("/api/sessions", () => new HttpResponse(null, { status: 500, statusText: "Server Error" })),
    );
    await expect(createSession(["it"])).rejects.toThrow("500");
  });
});

describe("observability endpoints", () => {
  it("listSweeps returns array", async () => {
    const result = await listSweeps();
    expect(Array.isArray(result)).toBe(true);
  });

  it("listTraces returns array", async () => {
    const result = await listTraces();
    expect(Array.isArray(result)).toBe(true);
  });

  it("getTraceStats returns counts", async () => {
    const result = await getTraceStats();
    expect(result.total_traces).toBeDefined();
  });

  it("getQuickActions returns actions", async () => {
    const result = await getQuickActions();
    expect(result.length).toBeGreaterThan(0);
    expect(result[0].id).toBe("triage");
  });

  it("getConfig returns config", async () => {
    const result = await getConfig();
    expect(result.has_api_key).toBe(false);
    expect(result.model).toBe("gpt-4.1-mini");
  });
});
