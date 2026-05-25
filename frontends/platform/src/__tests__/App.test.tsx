import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { server } from "../test/mocks/server";
import { http, HttpResponse } from "msw";
import App from "../App";

beforeEach(() => {
  vi.stubGlobal("EventSource", class MockES {
    onopen: (() => void) | null = null;
    onerror: (() => void) | null = null;
    onmessage: ((e: { data: string }) => void) | null = null;
    constructor() { setTimeout(() => this.onopen?.(), 0); }
    close() {}
  });
});

describe("App", () => {
  it("renders sidebar with nav items", async () => {
    render(<App />);
    expect(screen.getByText("IT Helpdesk")).toBeInTheDocument();
    expect(screen.getByText("HR & People")).toBeInTheDocument();
    expect(screen.getByText("Finance")).toBeInTheDocument();
    expect(screen.getByText("Engineering")).toBeInTheDocument();
    expect(screen.getByText("Customer Support")).toBeInTheDocument();
    expect(screen.getByText("Compliance")).toBeInTheDocument();
    expect(screen.getByText("Agent Console")).toBeInTheDocument();
    expect(screen.getByText("Command Timeline")).toBeInTheDocument();
    expect(screen.getByText("MCP Traffic")).toBeInTheDocument();
    expect(screen.getByText("Request Log")).toBeInTheDocument();
    expect(screen.getByText("Resource Map")).toBeInTheDocument();
    expect(screen.getByText("Trace Explorer")).toBeInTheDocument();
    expect(screen.getByText("Scorecard")).toBeInTheDocument();
  });

  it("default view shows IT Helpdesk content", async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.getByText("IT Helpdesk")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByText(/INC-1001/)).toBeInTheDocument();
    });
  });

  it("clicking Finance nav shows finance dashboard", async () => {
    const user = userEvent.setup();
    render(<App />);

    const financeNav = screen.getAllByText("Finance").find(
      (el) => el.closest(".sidebar-item") !== null,
    )!;
    await user.click(financeNav);

    await waitFor(() => {
      expect(screen.getByText(/EXP-1001/)).toBeInTheDocument();
    });
  });

  it("clicking Agent Console shows console layout with ServiceConnector", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByText("Agent Console"));

    await waitFor(() => {
      expect(screen.getByText("Connect Services")).toBeInTheDocument();
      expect(screen.getByText("IT Services")).toBeInTheDocument();
    });
  });

  it("shows Disconnected initially in sidebar footer", () => {
    render(<App />);
    expect(screen.getByText("Disconnected")).toBeInTheDocument();
  });

  it("console: sending a message creates session and shows reply", async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByText("Agent Console"));

    await waitFor(() => {
      expect(screen.getByText("Connect Services")).toBeInTheDocument();
    });

    const textarea = screen.getByPlaceholderText(/Describe a task/);
    await user.type(textarea, "Show open tickets");
    await user.click(screen.getByRole("button", { name: "Send" }));

    await waitFor(() => {
      expect(screen.getByText("Here are the results.")).toBeInTheDocument();
    });
  });
});
