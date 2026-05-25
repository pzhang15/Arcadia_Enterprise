import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import MockRequestLog from "../MockRequestLog";
import type { StreamEvent, MockRequestEvent } from "../../types";

const makeRequest = (overrides: Partial<MockRequestEvent> = {}): MockRequestEvent => ({
  type: "mock_request",
  timestamp: Date.now(),
  service: "slack",
  method: "GET",
  path: "/api/channels.list",
  query: {},
  status_code: 200,
  response_bytes: 2048,
  duration_ms: 12,
  ...overrides,
});

describe("MockRequestLog", () => {
  it("shows empty when no events", () => {
    render(<MockRequestLog events={[]} />);
    expect(screen.getByText(/No requests yet/)).toBeInTheDocument();
  });

  it("renders mock request events", () => {
    const events: StreamEvent[] = [
      makeRequest({ service: "slack", path: "/api/channels.list", method: "GET" }),
      makeRequest({ service: "github", path: "/repos/pulls", method: "POST", status_code: 201 }),
    ];
    render(<MockRequestLog events={events} />);
    expect(screen.getByText("/api/channels.list")).toBeInTheDocument();
    expect(screen.getByText("/repos/pulls")).toBeInTheDocument();
  });

  it("service filter works", async () => {
    const user = userEvent.setup();
    const events: StreamEvent[] = [
      makeRequest({ service: "slack", path: "/api/channels.list" }),
      makeRequest({ service: "github", path: "/repos/pulls" }),
    ];
    render(<MockRequestLog events={events} />);

    await user.click(screen.getByRole("button", { name: "slack" }));

    expect(screen.getByText("/api/channels.list")).toBeInTheDocument();
    expect(screen.queryByText("/repos/pulls")).not.toBeInTheDocument();
  });
});
