import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import App from "../App";
import { resetInvestigations } from "../lib/investigationStore";
import { clearSessionRun } from "../lib/sessionRunStore";

beforeEach(() => {
  resetInvestigations();
  clearSessionRun("abc123");
  clearSessionRun("new-sess");
  localStorage.removeItem("arcadia.session-run.v1");
  vi.stubGlobal(
    "EventSource",
    class MockES {
      onopen: (() => void) | null = null;
      onerror: (() => void) | null = null;
      onmessage: ((e: { data: string }) => void) | null = null;
      constructor() {
        setTimeout(() => this.onopen?.(), 0);
      }
      close() {}
    },
  );
});

function renderApp(path: string = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App shell", () => {
  it("renders the operations sidebar", () => {
    renderApp();
    expect(
      screen.getByRole("link", { name: /Inbox/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Dispatch/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Workspace Inspector/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Data Catalog/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Observability/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Evaluations/ }),
    ).toBeInTheDocument();
  });

  it("default route is the Inbox", async () => {
    renderApp();
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Inbox" }),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: /Dispatch agent/ }),
    ).toBeInTheDocument();
  });

  it("shows offline indicator initially in sidebar footer", () => {
    renderApp();
    expect(screen.getByText("Offline")).toBeInTheDocument();
  });
});

describe("Inbox", () => {
  it("loads sessions and renders them as investigation rows", async () => {
    renderApp();
    await waitFor(() => {
      expect(
        screen.getByText("Here are the open tickets..."),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Pending expenses reviewed.")).toBeInTheDocument();
  });

  it("filter chips narrow the visible list", async () => {
    const user = userEvent.setup();
    renderApp();
    await waitFor(() => {
      expect(
        screen.getByText("Here are the open tickets..."),
      ).toBeInTheDocument();
    });
    // Click P1 severity chip
    const p1Button = screen.getByRole("button", { name: /^P1$/ });
    await user.click(p1Button);
    // Since seeded investigations default to P3, the list should empty
    await waitFor(() => {
      expect(screen.getByText(/No matches/)).toBeInTheDocument();
    });
  });

  it("clicking the dispatch button navigates to the dispatch page", async () => {
    const user = userEvent.setup();
    renderApp();
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Inbox" })).toBeInTheDocument();
    });
    await user.click(
      screen.getByRole("button", { name: /Dispatch agent/ }),
    );
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /Dispatch agent/ }),
      ).toBeInTheDocument();
    });
  });
});

describe("Dispatch flow", () => {
  it("creates an investigation and navigates to its detail when submitted", async () => {
    const user = userEvent.setup();
    renderApp("/dispatch");

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: /Dispatch agent/ }),
      ).toBeInTheDocument();
    });

    // Default template should already be picked (Incident Response)
    const brief = screen.getByPlaceholderText(/Investigate the active P1/);
    await user.type(brief, "Investigate the P1 outage in payments-api");
    await user.click(
      screen.getByRole("button", { name: /Dispatch investigation/ }),
    );

    // Should navigate to /investigations/:id — the mocked POST returns id "new-sess"
    await waitFor(() => {
      expect(
        screen.getAllByText(/Investigate the P1 outage in payments-api/).length,
      ).toBeGreaterThan(0);
    });
  });
});

describe("Investigation Detail", () => {
  it("hydrates session history into the conversation", async () => {
    renderApp("/investigations/abc123");
    // The user's prompt appears once in chat (header may also show it as the title)
    await waitFor(() => {
      expect(
        screen.getByTestId("conversation-scroll"),
      ).toHaveTextContent("Found 4 tickets — 2 are duplicates of T-10243.");
    });
  });

  it("shows the investigation header with lifecycle actions", async () => {
    renderApp("/investigations/abc123");
    await waitFor(() => {
      expect(
        screen.getByTestId("conversation-scroll"),
      ).toHaveTextContent("Found 4 tickets — 2 are duplicates of T-10243.");
    });
    expect(screen.getByRole("button", { name: /Resolve/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Escalate/ })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Flag for review/ }),
    ).toBeInTheDocument();
  });

  it("hydrates run trace from the session trace API", async () => {
    renderApp("/investigations/abc123");
    await waitFor(() => {
      expect(screen.getByTestId("run-trace-scroll")).toBeInTheDocument();
    });
    expect(screen.getByText("Run Trace")).toBeInTheDocument();
  });

  it("renders scrollable conversation and run trace panes", async () => {
    renderApp("/investigations/abc123");
    await waitFor(() => {
      expect(screen.getByTestId("conversation-scroll")).toBeInTheDocument();
    });
    const conversation = screen.getByTestId("conversation-scroll");
    const trace = screen.getByTestId("run-trace-scroll");
    expect(conversation.className).toMatch(/overflow-y-auto/);
    expect(conversation.className).toMatch(/min-h-0/);
    expect(trace.className).toMatch(/overflow-y-auto/);
  });
});

describe("Workspace Inspector", () => {
  it("auto-binds to a session when ?session=<id> is in the URL", async () => {
    renderApp("/vfs?session=abc123");
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "Workspace Inspector" }),
      ).toBeInTheDocument();
    });
    await waitFor(() => {
      // The mock /vfs returns "tickets", "scratch", "README.md"
      expect(screen.getByText("tickets")).toBeInTheDocument();
      expect(screen.getByText("scratch")).toBeInTheDocument();
    });
  });

  it("falls back gracefully when a session has no workspace", async () => {
    renderApp("/vfs?session=ghi789");
    await waitFor(() => {
      expect(
        screen.getByText(/Workspace not available/),
      ).toBeInTheDocument();
    });
  });
});

describe("Data Catalog", () => {
  it("clicking the nav loads the mocked dataset", async () => {
    const user = userEvent.setup();
    renderApp();

    await user.click(screen.getByRole("link", { name: /Data Catalog/ }));

    await waitFor(() => {
      expect(screen.getByText(/INC-1001/)).toBeInTheDocument();
    });
    expect(screen.getByText(/\d+\s*records/)).toBeInTheDocument();
  });
});
