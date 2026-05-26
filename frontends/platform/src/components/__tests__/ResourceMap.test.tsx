import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ResourceMap from "../ResourceMap";
import type { StreamEvent, OpEvent } from "../../types";

const makeOp = (overrides: Partial<OpEvent> = {}): OpEvent => ({
  type: "op",
  agent: "agent-1",
  session: "sess-1",
  timestamp: Date.now(),
  op: "read",
  path: "/tickets/INC-1001.json",
  source: "disk",
  bytes: 1024,
  duration_ms: 3,
  ...overrides,
});

describe("ResourceMap", () => {
  it("shows empty when no events", () => {
    render(<ResourceMap events={[]} />);
    expect(screen.getByText(/No resource access recorded/)).toBeInTheDocument();
  });

  it("renders mount cards from op events", () => {
    const events: StreamEvent[] = [
      makeOp({ path: "/tickets/INC-1001.json", op: "read", bytes: 512 }),
      makeOp({ path: "/tickets/INC-1002.json", op: "read", bytes: 256 }),
      makeOp({ path: "/slack/channels/general/chat.jsonl", op: "read", bytes: 2048 }),
      makeOp({ path: "/slack/channels/general/chat.jsonl", op: "write", bytes: 128 }),
    ];
    render(<ResourceMap events={events} />);

    expect(screen.getAllByText("/tickets").length).toBeGreaterThan(0);
    expect(screen.getAllByText("/slack").length).toBeGreaterThan(0);
  });
});
