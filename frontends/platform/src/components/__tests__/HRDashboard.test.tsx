import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../test/mocks/server";
import HRDashboard from "../HRDashboard";

describe("HRDashboard", () => {
  it("renders loading state", () => {
    render(<HRDashboard />);
    expect(screen.getByText("Loading HR data...")).toBeInTheDocument();
  });

  it("renders employee cards with names", async () => {
    render(<HRDashboard />);
    expect(await screen.findByText("Alex Rivera")).toBeInTheDocument();
    expect(screen.getByText("Diana Park")).toBeInTheDocument();
    expect(screen.getByText("Sam Chen")).toBeInTheDocument();
    expect(screen.getByText("Employee Directory")).toBeInTheDocument();
  });

  it("renders stats with correct counts", async () => {
    render(<HRDashboard />);
    await screen.findByText("Alex Rivera");

    const totalStat = screen.getByText("Total Employees").closest(".stat-card");
    expect(totalStat).toHaveTextContent("3");

    const deptStat = screen.getByText("Departments").closest(".stat-card");
    expect(deptStat).toHaveTextContent("3");

    expect(screen.getByText("New Hires")).toBeInTheDocument();
    expect(screen.getByText("PTO Requests")).toBeInTheDocument();
  });

  it("shows empty state when no employees", async () => {
    server.use(
      http.get("/api/employees", () => HttpResponse.json([])),
    );
    render(<HRDashboard />);
    expect(await screen.findByText(/No employee data found/)).toBeInTheDocument();
  });
});
