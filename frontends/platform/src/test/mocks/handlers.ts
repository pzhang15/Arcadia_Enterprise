import { http, HttpResponse } from "msw";
import {
  ACCOUNTS,
  AUDITS,
  BUDGETS,
  CONTRACTS,
  DEPLOYMENTS,
  EMPLOYEES,
  ESCALATIONS,
  EXPENSES,
  INCIDENTS,
  POLICIES,
  PURCHASE_ORDERS,
  QUICK_ACTIONS,
  SESSIONS,
  TICKETS,
} from "../fixtures";

export const handlers = [
  http.get("/api/tickets/:queue", () => HttpResponse.json(TICKETS)),
  http.get("/api/finance/expenses", () => HttpResponse.json(EXPENSES)),
  http.get("/api/finance/purchase-orders", () => HttpResponse.json(PURCHASE_ORDERS)),
  http.get("/api/finance/invoices", () => HttpResponse.json([])),
  http.get("/api/finance/budgets", () => HttpResponse.json(BUDGETS)),
  http.get("/api/engineering/incidents", () => HttpResponse.json(INCIDENTS)),
  http.get("/api/engineering/deployments", () => HttpResponse.json(DEPLOYMENTS)),
  http.get("/api/engineering/metrics", () => HttpResponse.json([])),
  http.get("/api/employees", () => HttpResponse.json(EMPLOYEES)),
  http.get("/api/sheets/:id", () => HttpResponse.json({ title: "Sheet", rows: [] })),
  http.get("/api/customers/accounts", () => HttpResponse.json(ACCOUNTS)),
  http.get("/api/customers/escalations", () => HttpResponse.json(ESCALATIONS)),
  http.get("/api/compliance/contracts", () => HttpResponse.json(CONTRACTS)),
  http.get("/api/compliance/audits", () => HttpResponse.json(AUDITS)),
  http.get("/api/compliance/policies", () => HttpResponse.json(POLICIES)),
  http.get("/api/quick-actions", () => HttpResponse.json(QUICK_ACTIONS)),
  http.get("/api/results", () => HttpResponse.json([])),
  http.get("/api/traces", () => HttpResponse.json([])),
  http.get("/api/traces/stats/summary", () =>
    HttpResponse.json({ total_traces: 0, total_spans: 0 }),
  ),
  http.get("/api/config", () =>
    HttpResponse.json({ has_api_key: false, model: "gpt-4.1-mini" }),
  ),
  http.get("/api/sessions", () => HttpResponse.json(SESSIONS)),
  http.post("/api/sessions", () =>
    HttpResponse.json({ id: "new-sess", status: "ready", has_workspace: true, services: ["it"] }),
  ),
  http.post("/api/sessions/:id/message", () =>
    HttpResponse.json({ reply: "Here are the results.", status: "ready" }),
  ),
  http.get("/api/sessions/:id/history", () =>
    HttpResponse.json([
      { role: "user", content: "Show tickets", timestamp: Date.now() / 1000 - 60 },
      { role: "assistant", content: "Found 3 tickets.", timestamp: Date.now() / 1000 - 30 },
    ]),
  ),
];
