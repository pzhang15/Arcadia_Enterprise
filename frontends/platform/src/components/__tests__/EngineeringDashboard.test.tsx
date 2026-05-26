import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../test/mocks/server";
import EngineeringDashboard from "../EngineeringDashboard";

describe("EngineeringDashboard", () => {
  it("renders loading state", () => {
    render(<EngineeringDashboard />);
    expect(screen.getByText("Loading engineering data...")).toBeInTheDocument();
  });

  it("renders incidents with severity badges", async () => {
    render(<EngineeringDashboard />);
    expect(await screen.findByText("P99 latency > 2000ms on platform-api")).toBeInTheDocument();
    expect(screen.getByText("Okta SSO auth failures")).toBeInTheDocument();

    const criticalBadges = screen.getAllByText("critical");
    expect(criticalBadges.length).toBe(2);

    expect(screen.getByText("triggered")).toBeInTheDocument();
    expect(screen.getByText("resolved")).toBeInTheDocument();
  });

  it("renders deployment table", async () => {
    render(<EngineeringDashboard />);
    expect(await screen.findByText("Recent Deployments")).toBeInTheDocument();
    expect(screen.getByText("d4e5f6")).toBeInTheDocument();
    expect(screen.getByText("production")).toBeInTheDocument();
    expect(screen.getByText("Bob Martinez")).toBeInTheDocument();
  });

  it("renders stats correctly", async () => {
    render(<EngineeringDashboard />);
    await screen.findByText("P99 latency > 2000ms on platform-api");

    const activeStat = screen.getByText("Active Incidents").closest(".stat-card");
    expect(activeStat).toHaveTextContent("1");

    const criticalStat = screen.getByText("Critical").closest(".stat-card");
    expect(criticalStat).toHaveTextContent("2");

    const deployStat = screen.getByText("Deployments").closest(".stat-card");
    expect(deployStat).toHaveTextContent("1");

    const servicesStat = screen.getByText("Services").closest(".stat-card");
    expect(servicesStat).toHaveTextContent("2");
  });

  it("shows empty state when no data", async () => {
    server.use(
      http.get("/api/engineering/incidents", () => HttpResponse.json([])),
      http.get("/api/engineering/deployments", () => HttpResponse.json([])),
    );
    render(<EngineeringDashboard />);
    expect(await screen.findByText(/No engineering data found/)).toBeInTheDocument();
  });
});
