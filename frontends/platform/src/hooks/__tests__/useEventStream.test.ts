import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { useEventStream } from "../useEventStream";

class MockEventSource {
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  url: string;
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
  }

  static instances: MockEventSource[] = [];
  static reset() {
    MockEventSource.instances = [];
  }
}

beforeEach(() => {
  MockEventSource.reset();
  vi.stubGlobal("EventSource", MockEventSource);
});

describe("useEventStream", () => {
  it("opens EventSource with the given URL", () => {
    renderHook(() => useEventStream("/events"));
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toBe("/events");
  });

  it("sets connected to true on open", async () => {
    const { result } = renderHook(() => useEventStream("/events"));
    expect(result.current.connected).toBe(false);

    act(() => {
      MockEventSource.instances[0].onopen?.();
    });

    expect(result.current.connected).toBe(true);
  });

  it("sets connected to false on error", async () => {
    const { result } = renderHook(() => useEventStream("/events"));

    act(() => {
      MockEventSource.instances[0].onopen?.();
    });
    expect(result.current.connected).toBe(true);

    act(() => {
      MockEventSource.instances[0].onerror?.();
    });
    expect(result.current.connected).toBe(false);
  });

  it("parses incoming JSON messages into events array", () => {
    const { result } = renderHook(() => useEventStream("/events"));
    const es = MockEventSource.instances[0];

    act(() => {
      es.onmessage?.({
        data: JSON.stringify({ type: "command", timestamp: 1000, command: "ls /", agent: "a", session: "s", exit_code: 0, stdout: "" }),
      });
    });

    expect(result.current.events).toHaveLength(1);
    expect(result.current.events[0].type).toBe("command");
  });

  it("ignores malformed JSON", () => {
    const { result } = renderHook(() => useEventStream("/events"));
    const es = MockEventSource.instances[0];

    act(() => {
      es.onmessage?.({ data: "not json" });
    });

    expect(result.current.events).toHaveLength(0);
  });

  it("caps events at MAX_EVENTS (2000)", () => {
    const { result } = renderHook(() => useEventStream("/events"));
    const es = MockEventSource.instances[0];

    act(() => {
      for (let i = 0; i < 2050; i++) {
        es.onmessage?.({
          data: JSON.stringify({ type: "op", timestamp: i, op: "read", path: `/f${i}`, source: "s", bytes: 1, duration_ms: 1, agent: "a", session: "s" }),
        });
      }
    });

    expect(result.current.events.length).toBeLessThanOrEqual(2000);
  });

  it("clears events when clear is called", () => {
    const { result } = renderHook(() => useEventStream("/events"));
    const es = MockEventSource.instances[0];

    act(() => {
      es.onmessage?.({
        data: JSON.stringify({ type: "command", timestamp: 1, command: "ls", agent: "a", session: "s", exit_code: 0, stdout: "" }),
      });
    });
    expect(result.current.events).toHaveLength(1);

    act(() => {
      result.current.clear();
    });
    expect(result.current.events).toHaveLength(0);
  });

  it("closes EventSource on unmount", () => {
    const { unmount } = renderHook(() => useEventStream("/events"));
    const es = MockEventSource.instances[0];
    expect(es.closed).toBe(false);

    unmount();
    expect(es.closed).toBe(true);
  });
});
