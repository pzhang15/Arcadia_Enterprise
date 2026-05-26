import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../test/mocks/server";
import ComplianceDashboard from "../ComplianceDashboard";

describe("ComplianceDashboard", () => {
  it("renders loading state", () => {
    render(<ComplianceDashboard />);
    expect(screen.getByText("Loading compliance data...")).toBeInTheDocument();
  });

  it("renders contracts", async () => {
    render(<ComplianceDashboard />);
    expect(await screen.findByText("Contract Review Queue")).toBeInTheDocument();
    expect(screen.getByText("CTR-1001")).toBeInTheDocument();
    expect(screen.getByText("CTR-1007")).toBeInTheDocument();
    expect(screen.getByText("GlobalTech")).toBeInTheDocument();
    expect(screen.getByText("DataStream Inc")).toBeInTheDocument();
  });

  it("renders audit progress", async () => {
    render(<ComplianceDashboard />);
    expect(await screen.findByText("Audit Progress")).toBeInTheDocument();
    expect(screen.getByText("SOC2 Type II")).toBeInTheDocument();
    expect(screen.getByText("1/3")).toBeInTheDocument();
    expect(screen.getByText("33% complete")).toBeInTheDocument();
  });

  it("renders policy acknowledgment rates", async () => {
    render(<ComplianceDashboard />);
    expect(await screen.findByText("Policy Acknowledgment Tracker")).toBeInTheDocument();
    expect(screen.getByText("Data Retention Policy")).toBeInTheDocument();
    expect(screen.getByText("1/2")).toBeInTheDocument();
    expect(screen.getByText("50% acknowledged")).toBeInTheDocument();
  });

  it("renders stats correctly", async () => {
    render(<ComplianceDashboard />);
    await screen.findByText("CTR-1001");

    const reviewStat = screen.getByText("Contracts in Review").closest(".stat-card");
    expect(reviewStat).toHaveTextContent("1");

    const auditStat = screen.getByText("Audit Items Remaining").closest(".stat-card");
    expect(auditStat).toHaveTextContent("2");

    const ackStat = screen.getByText("Policy Ack Rate").closest(".stat-card");
    expect(ackStat).toHaveTextContent("50%");

    const policyStat = screen.getByText("Total Policies").closest(".stat-card");
    expect(policyStat).toHaveTextContent("1");
  });

  it("shows empty state when no data", async () => {
    server.use(
      http.get("/api/compliance/contracts", () => HttpResponse.json([])),
      http.get("/api/compliance/audits", () => HttpResponse.json([])),
      http.get("/api/compliance/policies", () => HttpResponse.json([])),
    );
    render(<ComplianceDashboard />);
    expect(await screen.findByText(/No compliance data found/)).toBeInTheDocument();
  });
});
