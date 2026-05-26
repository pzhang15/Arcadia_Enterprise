import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import LiveExecutionView from "../LiveExecutionView";
import type { StreamEvent, CommandEvent } from "../../types";

const makeCommand = (overrides: Partial<CommandEvent> = {}): CommandEvent => ({
  type: "command",
  agent: "agent-1",
  session: "sess-1",
  timestamp: Date.now(),
  command: "ls /tickets",
  exit_code: 0,
  stdout: null,
  ...overrides,
});

describe("LiveExecutionView", () => {
  it("shows waiting message when no sessionId", () => {
    render(<LiveExecutionView events={[]} sessionId={null} />);
    expect(screen.getByText(/No active session/)).toBeInTheDocument();
  });

  it("renders commands for matching session", () => {
    const events: StreamEvent[] = [
      makeCommand({ session: "my-sess", command: "cat /tickets/INC-1001.json" }),
      makeCommand({ session: "my-sess", command: "ls /slack/channels" }),
    ];
    render(<LiveExecutionView events={events} sessionId="my-sess" />);
    expect(screen.getByText("cat /tickets/INC-1001.json")).toBeInTheDocument();
    expect(screen.getByText("ls /slack/channels")).toBeInTheDocument();
  });

  it("ignores events from other sessions", () => {
    const events: StreamEvent[] = [
      makeCommand({ session: "other-sess", command: "echo secret" }),
      makeCommand({ session: "my-sess", command: "ls /finance" }),
    ];
    render(<LiveExecutionView events={events} sessionId="my-sess" />);
    expect(screen.getByText("ls /finance")).toBeInTheDocument();
    expect(screen.queryByText("echo secret")).not.toBeInTheDocument();
  });
});
