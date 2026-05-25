import type {
  Audit,
  BudgetData,
  Contract,
  CustomerAccount,
  Deployment,
  Employee,
  Escalation,
  Expense,
  PagerDutyIncident,
  Policy,
  PurchaseOrder,
  Ticket,
} from "../types";

export const TICKETS: Ticket[] = [
  {
    ticket_id: "INC-1001",
    subject: "Laptop not arrived for Alex Rivera",
    body: "New hire laptop missing",
    requester: { id: "U101", name: "Alex Rivera", email: "alex@test.com" },
    assignee: { id: "U104", name: "Priya Patel", email: "priya@test.com" },
    queue: "it-helpdesk",
    status: "open",
    priority: "P2",
    created_at: "2026-05-10T09:00:00Z",
    updated_at: "2026-05-10T10:00:00Z",
    tags: ["onboarding", "hardware"],
    related_tickets: [],
    comments: [
      { author: "Priya Patel", ts: "2026-05-10T11:00:00Z", body: "Checking with procurement" },
    ],
  },
  {
    ticket_id: "INC-1002",
    subject: "AWS access for Alex Rivera",
    body: "Need AWS access for platform team",
    requester: { id: "U101", name: "Alex Rivera", email: "alex@test.com" },
    assignee: { id: "U103", name: "Sam Chen", email: "sam@test.com" },
    queue: "it-helpdesk",
    status: "in_progress",
    priority: "P3",
    created_at: "2026-05-11T09:00:00Z",
    updated_at: "2026-05-12T09:00:00Z",
    tags: ["access", "aws"],
    related_tickets: ["INC-1001"],
    comments: [],
  },
  {
    ticket_id: "INC-1003",
    subject: "Printer jammed on 3rd floor",
    body: "3rd floor printer is jammed again",
    requester: { id: "U107", name: "Bob Lee", email: "bob@test.com" },
    assignee: null,
    queue: "it-helpdesk",
    status: "resolved",
    priority: "P4",
    created_at: "2026-05-12T14:00:00Z",
    updated_at: "2026-05-12T16:00:00Z",
    tags: ["hardware"],
    related_tickets: [],
    comments: [],
  },
];

export const EXPENSES: Expense[] = [
  {
    expense_id: "EXP-1001",
    submitter: { id: "U201", name: "Frank Osei", email: "frank@test.com" },
    department: "Engineering",
    amount: 1250.0,
    currency: "USD",
    category: "travel",
    description: "Conference travel",
    submitted_at: "2026-05-13T10:00:00Z",
    status: "pending",
    approver: null,
    line_items: [{ description: "Flight", amount: 800 }, { description: "Hotel", amount: 450 }],
  },
  {
    expense_id: "EXP-0991",
    submitter: { id: "U212", name: "Bob Martinez", email: "bob.m@test.com" },
    department: "Engineering/SRE",
    amount: 2100.0,
    currency: "USD",
    category: "equipment",
    description: "Monitor upgrade",
    submitted_at: "2026-05-01T10:00:00Z",
    status: "approved",
    approver: "Rachel Nguyen",
    line_items: [{ description: "Monitor", amount: 2100 }],
  },
];

export const PURCHASE_ORDERS: PurchaseOrder[] = [
  {
    po_id: "PO-1001",
    requester: { id: "U103", name: "Sam Chen", email: "sam@test.com" },
    vendor: "Dell Technologies",
    items: [{ description: "Laptops", quantity: 5, unit_price: 1800 }],
    total: 9000,
    status: "open",
    created_at: "2026-05-10T09:00:00Z",
    approved_by: null,
    department: "IT",
  },
];

export const BUDGETS: BudgetData = {
  departments: [
    { name: "Engineering", budget: 500000, spent: 350000, remaining: 150000, status: "on_track" },
    { name: "Marketing", budget: 200000, spent: 180000, remaining: 20000, status: "at_risk" },
  ],
};

export const INCIDENTS: PagerDutyIncident[] = [
  {
    id: "INC-5521",
    title: "P99 latency > 2000ms on platform-api",
    status: "triggered",
    severity: "critical",
    service: "platform-api",
    assignee: "Nina Gupta",
    created_at: "2026-05-15T08:00:00Z",
  },
  {
    id: "INC-5518",
    title: "Okta SSO auth failures",
    status: "resolved",
    severity: "critical",
    service: "auth-service",
    assignee: "Sam Chen",
    created_at: "2026-04-22T09:14:00Z",
  },
];

export const DEPLOYMENTS: Deployment[] = [
  {
    id: "d4e5f6",
    ref: "main",
    environment: "production",
    created_at: "2026-05-15T06:30:00Z",
    status: "success",
    creator: "Bob Martinez",
  },
];

export const EMPLOYEES: Employee[] = [
  { id: "U101", handle: "alex", name: "Alex Rivera", email: "alex@northhill.com", title: "Software Engineer", department: "Platform" },
  { id: "U102", handle: "diana", name: "Diana Park", email: "diana@northhill.com", title: "HR Partner", department: "People" },
  { id: "U103", handle: "sam", name: "Sam Chen", email: "sam@northhill.com", title: "IT Lead", department: "IT" },
];

export const ACCOUNTS: CustomerAccount[] = [
  {
    account_id: "ACCT-1001",
    company_name: "GlobalTech",
    tier: "enterprise",
    arr: 480000,
    health_score: 45,
    csm: "Sarah Kim",
    renewal_date: "2026-08-15",
    contacts: [{ name: "John Doe", email: "john@globaltech.com", role: "CTO" }],
    products: ["Platform", "Analytics"],
  },
  {
    account_id: "ACCT-1002",
    company_name: "MidCo",
    tier: "standard",
    arr: 120000,
    health_score: 88,
    csm: "Sarah Kim",
    renewal_date: "2027-01-15",
    contacts: [],
    products: ["Platform"],
  },
];

export const ESCALATIONS: Escalation[] = [
  {
    escalation_id: "ESC-1001",
    account_id: "ACCT-1001",
    severity: "high",
    description: "Login failures impacting GlobalTech",
    linked_ticket: "CS-1001",
    created_at: "2026-05-15T09:00:00Z",
    status: "active",
    owner: "Sarah Kim",
  },
  {
    escalation_id: "ESC-1002",
    account_id: "ACCT-1002",
    severity: "medium",
    description: "Data sync issues",
    linked_ticket: "CS-1002",
    created_at: "2026-05-14T10:00:00Z",
    status: "resolved",
    owner: "Mike Johnson",
  },
];

export const CONTRACTS: Contract[] = [
  {
    contract_id: "CTR-1001",
    counterparty: "GlobalTech",
    type: "MSA",
    value: 480000,
    start_date: "2025-08-15",
    end_date: "2026-08-15",
    status: "active",
    owner: "Michael Torres",
    review_notes: "",
  },
  {
    contract_id: "CTR-1007",
    counterparty: "DataStream Inc",
    type: "SaaS",
    value: 36000,
    start_date: "2026-05-01",
    end_date: "2027-05-01",
    status: "in_review",
    owner: "Emily Foster",
    review_notes: "Pending legal review",
  },
];

export const AUDITS: Audit[] = [
  {
    audit_id: "AUDIT-2026-SOC2",
    framework: "SOC2 Type II",
    status: "in_progress",
    due_date: "2026-06-30",
    checklist: [
      { name: "Access control review", status: "completed", owner: "Derek Wong", evidence_link: "/compliance/evidence/ac1" },
      { name: "Encryption audit", status: "in_progress", owner: "Sam Chen", evidence_link: "" },
      { name: "Vendor risk assessment", status: "pending", owner: "Emily Foster", evidence_link: "" },
    ],
  },
];

export const POLICIES: Policy[] = [
  {
    policy_id: "POL-1001",
    title: "Data Retention Policy",
    version: "2.1",
    effective_date: "2026-01-01",
    acknowledgments: [
      { user_id: "U101", acked_at: "2026-01-15T10:00:00Z" },
      { user_id: "U102", acked_at: null },
    ],
  },
];

export const QUICK_ACTIONS = [
  { id: "triage", label: "Triage IT helpdesk queue", services: ["it", "hr"], task: "Triage all open IT tickets." },
  { id: "expenses", label: "Review pending expenses", services: ["finance"], task: "Review all pending expense reports." },
];

export const SESSIONS = [
  { id: "abc123", status: "ready", services: ["it", "hr"], created_at: Date.now() / 1000 - 300, message_count: 4, last_message: "Here are the open tickets..." },
  { id: "def456", status: "ready", services: ["finance"], created_at: Date.now() / 1000 - 3600, message_count: 2, last_message: "Pending expenses reviewed." },
];
