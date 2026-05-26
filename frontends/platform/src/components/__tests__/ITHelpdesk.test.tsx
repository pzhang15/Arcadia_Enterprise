import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { server } from "../../test/mocks/server";
import ITHelpdesk from "../ITHelpdesk";

describe("ITHelpdesk", () => {
  it("renders loading state", () => {
    render(<ITHelpdesk />);
    expect(screen.getByText("Loading tickets...")).toBeInTheDocument();
  });

  it("renders tickets after load", async () => {
    render(<ITHelpdesk />);
    expect(await screen.findByText("INC-1001")).toBeInTheDocument();
    expect(screen.getByText("INC-1002")).toBeInTheDocument();
    expect(screen.getByText("INC-1003")).toBeInTheDocument();
  });

  it("renders stats correctly", async () => {
    render(<ITHelpdesk />);
    await screen.findByText("INC-1001");

    expect(screen.getByText("Total Tickets")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();

    const openStat = screen.getByText("Open", { selector: ".stat-label" }).closest(".stat-card");
    expect(openStat).toHaveTextContent("1");

    const inProgressStat = screen.getByText("In Progress", { selector: ".stat-label" }).closest(".stat-card");
    expect(inProgressStat).toHaveTextContent("1");

    const resolvedStat = screen.getByText("Resolved", { selector: ".stat-label" }).closest(".stat-card");
    expect(resolvedStat).toHaveTextContent("1");
  });

  it("filters by status", async () => {
    const user = userEvent.setup();
    render(<ITHelpdesk />);
    await screen.findByText("INC-1001");

    const openBtn = screen.getByRole("button", { name: "Open" });
    await user.click(openBtn);

    expect(screen.getByText("INC-1001")).toBeInTheDocument();
    expect(screen.queryByText("INC-1002")).not.toBeInTheDocument();
    expect(screen.queryByText("INC-1003")).not.toBeInTheDocument();
  });

  it("expands ticket to show body text", async () => {
    const user = userEvent.setup();
    render(<ITHelpdesk />);
    await screen.findByText("INC-1001");

    const row = screen.getByText("Laptop not arrived for Alex Rivera").closest("tr")!;
    await user.click(row);

    expect(await screen.findByText("New hire laptop missing")).toBeInTheDocument();
    expect(screen.getByText("Checking with procurement")).toBeInTheDocument();
  });

  it("shows empty state when no tickets", async () => {
    server.use(
      http.get("/api/tickets/:queue", () => HttpResponse.json([])),
    );
    render(<ITHelpdesk />);
    expect(await screen.findByText(/No tickets found/)).toBeInTheDocument();
  });
});
