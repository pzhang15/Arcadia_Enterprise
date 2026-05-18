export interface Employee {
  id: string;
  handle: string;
  name: string;
  email: string;
  title: string;
  department?: string;
}

export interface Ticket {
  ticket_id: string;
  subject: string;
  body: string;
  requester: { id: string; name: string; email: string };
  assignee: { id: string; name: string; email: string } | null;
  queue: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at: string;
  tags: string[];
  related_tickets: string[];
  comments: { author: string; ts: string; body: string }[];
}

export interface Expense {
  expense_id: string;
  submitter: { id: string; name: string; email: string };
  department: string;
  amount: number;
  currency: string;
  category: string;
  description: string;
  submitted_at: string;
  status: string;
  approver: string | null;
  line_items: { description: string; amount: number }[];
}

export interface PurchaseOrder {
  po_id: string;
  requester: { id: string; name: string; email: string };
  vendor: string;
  items: { description: string; quantity: number; unit_price: number }[];
  total: number;
  status: string;
  created_at: string;
  approved_by: string | null;
  department: string;
}

export interface Invoice {
  invoice_id: string;
  vendor: string;
  amount: number;
  due_date: string;
  po_reference: string | null;
  status: string;
  department: string;
}

export interface CustomerAccount {
  account_id: string;
  company_name: string;
  tier: string;
  arr: number;
  health_score: number;
  csm: string;
  renewal_date: string;
  contacts: { name: string; email: string; role: string }[];
  products: string[];
}

export interface Escalation {
  escalation_id: string;
  account_id: string;
  severity: string;
  description: string;
  linked_ticket: string;
  created_at: string;
  status: string;
  owner: string;
}

export interface Contract {
  contract_id: string;
  counterparty: string;
  type: string;
  value: number;
  start_date: string;
  end_date: string;
  status: string;
  owner: string;
  review_notes: string;
}

export interface Audit {
  audit_id: string;
  framework: string;
  status: string;
  due_date: string;
  checklist: { name: string; status: string; owner: string; evidence_link: string }[];
}

export interface Policy {
  policy_id: string;
  title: string;
  version: string;
  effective_date: string;
  acknowledgments: { user_id: string; acked_at: string | null }[];
}

export interface PagerDutyIncident {
  id: string;
  title: string;
  status: string;
  severity: string;
  service: string;
  assignee: string;
  created_at: string;
}

export interface Deployment {
  id: string;
  ref: string;
  environment: string;
  created_at: string;
  status: string;
  creator: string;
}

export interface BudgetData {
  departments: { name: string; budget: number; spent: number; remaining: number; status: string }[];
}
