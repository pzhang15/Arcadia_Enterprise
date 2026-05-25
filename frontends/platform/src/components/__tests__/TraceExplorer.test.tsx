import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { server } from "../../test/mocks/server";
import { http, HttpResponse } from "msw";
import TraceExplorer from "../TraceExplorer";

describe("TraceExplorer", () => {
  it("shows loading state", () => {
    render(<TraceExplorer />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows empty state when no traces", async () => {
    render(<TraceExplorer />);
    await waitFor(() => {
      expect(screen.getByText(/No traces yet/)).toBeInTheDocument();
    });
  });

  it("renders traces when data exists", async () => {
    server.use(
      http.get("/api/traces", () =>
        HttpResponse.json([
          {
            trace_id: "t1",
            name: "ls /tickets",
            start_time_ms: 1000,
            end_time_ms: 1500,
            status: 0,
            attributes: { command: "ls /tickets" },
            metrics: { bytes_read: 1024, bytes_written: 0, api_calls: 1, cache_hits: 0, cache_misses: 1 },
            session_id: "sess1",
            agent_id: "agent1",
            child_count: 2,
          },
        ]),
      ),
      http.get("/api/traces/stats/summary", () =>
        HttpResponse.json({ total_traces: 1, total_spans: 3 }),
      ),
    );

    render(<TraceExplorer />);

    await waitFor(() => {
      expect(screen.getByText("ls /tickets")).toBeInTheDocument();
    });
    const statValues = screen.getAllByClassName
      ? document.querySelectorAll(".stat-value")
      : [];
    expect(screen.getByText("Total Traces")).toBeInTheDocument();
    expect(screen.getByText("Total Spans")).toBeInTheDocument();
  });
});
