import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../test/mocks/server";
import FinanceDashboard from "../FinanceDashboard";

describe("FinanceDashboard", () => {
  it("renders loading state", () => {
    render(<FinanceDashboard />);
    expect(screen.getByText("Loading finance data...")).toBeInTheDocument();
  });

  it("renders expense data", async () => {
    render(<FinanceDashboard />);
    expect(await screen.findByText("EXP-1001")).toBeInTheDocument();
    expect(screen.getByText("EXP-0991")).toBeInTheDocument();
    expect(screen.getByText("Expense Reports")).toBeInTheDocument();
  });

  it("renders purchase order data", async () => {
    render(<FinanceDashboard />);
    expect(await screen.findByText("PO-1001")).toBeInTheDocument();
    expect(screen.getByText("Dell Technologies")).toBeInTheDocument();
    expect(screen.getByText("Purchase Orders")).toBeInTheDocument();
  });

  it("renders budget departments with percentage", async () => {
    render(<FinanceDashboard />);
    await screen.findByText("Budget Summary by Department");

    const budgetNodes = screen.getAllByText("Engineering");
    expect(budgetNodes.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Marketing")).toBeInTheDocument();
    expect(screen.getByText("70% used")).toBeInTheDocument();
    expect(screen.getByText("90% used")).toBeInTheDocument();
  });

  it("renders stats correctly", async () => {
    render(<FinanceDashboard />);
    await screen.findByText("EXP-1001");

    expect(screen.getByText("Pending Expenses")).toBeInTheDocument();
    const pendingStat = screen.getByText("Pending Expenses").closest(".stat-card");
    expect(pendingStat).toHaveTextContent("$1,250.00");

    expect(screen.getByText("Open POs")).toBeInTheDocument();
    const openPoStat = screen.getByText("Open POs").closest(".stat-card");
    expect(openPoStat).toHaveTextContent("1");

    expect(screen.getByText("Budget Utilization")).toBeInTheDocument();
    expect(screen.getByText("76%")).toBeInTheDocument();

    expect(screen.getByText("Total Budget")).toBeInTheDocument();
    expect(screen.getByText("$700,000.00")).toBeInTheDocument();
  });

  it("shows empty state when no data", async () => {
    server.use(
      http.get("/api/finance/expenses", () => HttpResponse.json([])),
      http.get("/api/finance/purchase-orders", () => HttpResponse.json([])),
      http.get("/api/finance/budgets", () => HttpResponse.json({ departments: [] })),
    );
    render(<FinanceDashboard />);
    expect(await screen.findByText(/No finance data found/)).toBeInTheDocument();
  });
});
