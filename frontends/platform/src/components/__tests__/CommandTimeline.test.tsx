import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import CommandTimeline from "../CommandTimeline";
import type { StreamEvent, CommandEvent, OpEvent, MockRequestEvent } from "../../types";

const makeCommand = (overrides: Partial<CommandEvent> = {}): CommandEvent => ({
  type: "command",
  agent: "agent-1",
  session: "sess-1",
  timestamp: Date.now(),
  command: "ls /tickets",
  exit_code: 0,
  stdout: "ticket-1.json\nticket-2.json",
  ...overrides,
});

const makeOp = (overrides: Partial<OpEvent> = {}): OpEvent => ({
  type: "op",
  agent: "agent-1",
  session: "sess-1",
  timestamp: Date.now(),
  op: "read",
  path: "/tickets/ticket-1.json",
  source: "disk",
  bytes: 512,
  duration_ms: 2,
  ...overrides,
});

const makeMockRequest = (): MockRequestEvent => ({
  type: "mock_request",
  timestamp: Date.now(),
  service: "slack",
  method: "GET",
  path: "/api/channels",
  query: {},
  status_code: 200,
  response_bytes: 1024,
  duration_ms: 5,
});

describe("CommandTimeline", () => {
  it("renders empty when no events", () => {
    render(<CommandTimeline events={[]} onClear={vi.fn()} />);
    expect(screen.getByText(/Waiting for commands/)).toBeInTheDocument();
  });

  it("renders command events in table", () => {
    const events: StreamEvent[] = [
      makeCommand({ command: "cat /tickets/INC-1001.json" }),
      makeCommand({ command: "ls /slack/channels", exit_code: 0 }),
    ];
    render(<CommandTimeline events={events} onClear={vi.fn()} />);
    expect(screen.getByText("cat /tickets/INC-1001.json")).toBeInTheDocument();
    expect(screen.getByText("ls /slack/channels")).toBeInTheDocument();
  });

  it("clicking row expands stdout", async () => {
    const user = userEvent.setup();
    const events: StreamEvent[] = [
      makeCommand({ command: "ls /tickets", stdout: "ticket-1.json" }),
    ];
    render(<CommandTimeline events={events} onClear={vi.fn()} />);

    expect(screen.queryByText("ticket-1.json")).not.toBeInTheDocument();

    await user.click(screen.getByText("ls /tickets"));
    expect(screen.getByText("ticket-1.json")).toBeInTheDocument();
  });

  it("clear button calls onClear", async () => {
    const user = userEvent.setup();
    const onClear = vi.fn();
    render(<CommandTimeline events={[makeCommand()]} onClear={onClear} />);

    await user.click(screen.getByRole("button", { name: "Clear" }));
    expect(onClear).toHaveBeenCalledTimes(1);
  });

  it("filters non-command events", () => {
    const events: StreamEvent[] = [
      makeMockRequest(),
      makeOp(),
      makeCommand({ command: "echo hello" }),
    ];
    render(<CommandTimeline events={events} onClear={vi.fn()} />);
    expect(screen.getByText("echo hello")).toBeInTheDocument();
    expect(screen.queryByText("/api/channels")).not.toBeInTheDocument();
  });
});
