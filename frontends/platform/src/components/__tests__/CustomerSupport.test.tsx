import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../test/mocks/server";
import CustomerSupport from "../CustomerSupport";

describe("CustomerSupport", () => {
  it("renders loading state", () => {
    render(<CustomerSupport />);
    expect(screen.getByText("Loading customer data...")).toBeInTheDocument();
  });

  it("renders support tickets", async () => {
    render(<CustomerSupport />);
    expect(await screen.findByText("Support Queue")).toBeInTheDocument();
    expect(screen.getByText("INC-1001")).toBeInTheDocument();
    expect(screen.getByText("INC-1002")).toBeInTheDocument();
    expect(screen.getByText("INC-1003")).toBeInTheDocument();
  });

  it("renders escalations", async () => {
    render(<CustomerSupport />);
    expect(await screen.findByText("ESC-1001")).toBeInTheDocument();
    expect(screen.getByText("ESC-1002")).toBeInTheDocument();
    expect(screen.getByText("Login failures impacting GlobalTech")).toBeInTheDocument();
    expect(screen.getByText("Data sync issues")).toBeInTheDocument();
  });

  it("renders account cards with health scores", async () => {
    render(<CustomerSupport />);
    expect(await screen.findByText("Account Health")).toBeInTheDocument();
    expect(screen.getByText("GlobalTech")).toBeInTheDocument();
    expect(screen.getByText("MidCo")).toBeInTheDocument();
    expect(screen.getByText("45")).toBeInTheDocument();
    expect(screen.getByText("88")).toBeInTheDocument();
  });

  it("renders stats correctly", async () => {
    render(<CustomerSupport />);
    await screen.findByText("INC-1001");

    const openStat = screen.getByText("Open Tickets").closest(".stat-card");
    expect(openStat).toHaveTextContent("2");

    const escalationStat = screen.getByText("Escalations", { selector: ".stat-label" }).closest(".stat-card");
    expect(escalationStat).toHaveTextContent("1");

    const atRiskStat = screen.getByText("At-Risk Accounts").closest(".stat-card");
    expect(atRiskStat).toHaveTextContent("1");

    const totalStat = screen.getByText("Total Accounts").closest(".stat-card");
    expect(totalStat).toHaveTextContent("2");
  });

  it("shows empty state when no data", async () => {
    server.use(
      http.get("/api/tickets/:queue", () => HttpResponse.json([])),
      http.get("/api/customers/accounts", () => HttpResponse.json([])),
      http.get("/api/customers/escalations", () => HttpResponse.json([])),
    );
    render(<CustomerSupport />);
    expect(await screen.findByText(/No customer data found/)).toBeInTheDocument();
  });
});
