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
    HttpResponse.json({ has_api_key: false, model: "gpt-4.1-mini", reasoning: true }),
  ),
  http.get("/api/investigations", () => HttpResponse.json([])),
  http.get("/api/investigations/:id", ({ params }) =>
    HttpResponse.json({
      sessionId: params.id,
      title: "Investigation",
      templateId: "custom",
      severity: "P3",
      status: "running",
      trigger: "manual",
      authority: "read_only",
      createdAt: 1,
      updatedAt: 1,
    }),
  ),
  http.post("/api/investigations", async ({ request }) =>
    HttpResponse.json(await request.json()),
  ),
  http.patch("/api/investigations/:id", async ({ request, params }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json({ ...body, sessionId: params.id });
  }),
  http.delete("/api/investigations/:id", () =>
    HttpResponse.json({ deleted: true }),
  ),
  http.get("/api/sessions", () => HttpResponse.json(SESSIONS)),
  http.post("/api/sessions", () =>
    HttpResponse.json({ id: "new-sess", status: "ready", has_workspace: true, services: ["it"] }),
  ),
  http.post("/api/sessions/:id/message/stream", () => {
    const timestamp = Date.now();
    const events = [
      {
        type: "RUN_STARTED",
        timestamp,
        thread_id: "new-sess",
        run_id: "run-test",
      },
      {
        type: "STEP_STARTED",
        timestamp,
        step_id: "step-1",
        step_name: "Plan and execute",
      },
      {
        type: "THINKING_START",
        timestamp,
        thinking_id: "think-1",
        step_id: "step-1",
      },
      {
        type: "THINKING_CONTENT",
        timestamp,
        thinking_id: "think-1",
        delta: "I should look up tickets and summarize.",
      },
      {
        type: "THINKING_END",
        timestamp,
        thinking_id: "think-1",
      },
      {
        type: "TOOL_CALL_START",
        timestamp,
        tool_call_id: "tc-1",
        tool_name: "vfs.list",
        step_id: "step-1",
      },
      {
        type: "TOOL_CALL_ARGS",
        timestamp,
        tool_call_id: "tc-1",
        delta: '{"path": "/tickets"}',
      },
      {
        type: "TOOL_CALL_END",
        timestamp,
        tool_call_id: "tc-1",
      },
      {
        type: "TOOL_CALL_RESULT",
        timestamp,
        tool_call_id: "tc-1",
        result: '{"entries": []}',
        exit_code: 0,
      },
      {
        type: "TEXT_MESSAGE_START",
        timestamp,
        message_id: "msg-test",
        role: "assistant",
      },
      {
        type: "TEXT_MESSAGE_CONTENT",
        timestamp,
        message_id: "msg-test",
        delta: "Here are the results.",
      },
      {
        type: "TEXT_MESSAGE_END",
        timestamp,
        message_id: "msg-test",
      },
      {
        type: "STEP_FINISHED",
        timestamp,
        step_id: "step-1",
      },
      {
        type: "RUN_FINISHED",
        timestamp,
        thread_id: "new-sess",
        run_id: "run-test",
      },
    ];
    return new HttpResponse(
      events.map((event) => `data: ${JSON.stringify(event)}\n\n`).join(""),
      { headers: { "Content-Type": "text/event-stream" } },
    );
  }),
  http.post("/api/sessions/:id/message", () =>
    HttpResponse.json({ reply: "Here are the results.", status: "ready" }),
  ),
  http.get("/api/sessions/:id/trace", ({ params }) => {
    const id = params.id as string;
    if (id === "abc123") {
      const ts = Date.now() - 120_000;
      return HttpResponse.json({
        session_id: id,
        event_count: 4,
        events: [
          {
            type: "RUN_STARTED",
            timestamp: ts,
            thread_id: id,
            run_id: "run-abc",
          },
          {
            type: "TEXT_MESSAGE_START",
            timestamp: ts + 1,
            message_id: "msg-abc",
            role: "assistant",
          },
          {
            type: "TEXT_MESSAGE_CONTENT",
            timestamp: ts + 2,
            message_id: "msg-abc",
            delta: "Found 4 tickets — 2 are duplicates of T-10243.",
          },
          {
            type: "TEXT_MESSAGE_END",
            timestamp: ts + 3,
            message_id: "msg-abc",
          },
          {
            type: "RUN_FINISHED",
            timestamp: ts + 4,
            thread_id: id,
            run_id: "run-abc",
          },
        ],
      });
    }
    return HttpResponse.json({ session_id: id, event_count: 0, events: [] });
  }),
  http.get("/api/sessions/:id/history", ({ params }) => {
    const id = params.id as string;
    if (id === "abc123") {
      return HttpResponse.json([
        { role: "user", content: "Triage the IT queue", timestamp: Date.now() / 1000 - 180 },
        { role: "assistant", content: "Found 4 tickets — 2 are duplicates of T-10243.", timestamp: Date.now() / 1000 - 120 },
      ]);
    }
    return HttpResponse.json([
      { role: "user", content: "Show tickets", timestamp: Date.now() / 1000 - 60 },
      { role: "assistant", content: "Found 3 tickets.", timestamp: Date.now() / 1000 - 30 },
    ]);
  }),
  http.get("/api/sessions/:id/status", ({ params }) =>
    HttpResponse.json({
      id: params.id,
      status: "ready",
      services: ["it", "hr"],
      created_at: Date.now() / 1000 - 300,
      message_count: 2,
      has_workspace: true,
      error: null,
    }),
  ),
  http.get("/api/sessions/:id/vfs", ({ params }) => {
    if ((params.id as string) === "ghi789") {
      return HttpResponse.json({ error: "workspace not available" }, { status: 400 });
    }
    return HttpResponse.json({
      entries: [
        { name: "tickets", type: "dir" },
        { name: "scratch", type: "dir" },
        { name: "README.md", type: "file", size: 482 },
      ],
    });
  }),
];
