import { render, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../test/mocks/server";
import ScoreCardDashboard from "../ScoreCardDashboard";

describe("ScoreCardDashboard", () => {
  it("renders empty state when no sweeps", async () => {
    server.use(
      http.get("/api/results", () => HttpResponse.json([], { status: 500 })),
    );
    render(<ScoreCardDashboard />);
    expect(await screen.findByText(/No eval results available/)).toBeInTheDocument();
  });

  it("shows header when sweeps list is empty", async () => {
    render(<ScoreCardDashboard />);
    expect(await screen.findByText("Scorecard Dashboard")).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("renders sweep selector when sweeps exist", async () => {
    server.use(
      http.get("/api/results", () =>
        HttpResponse.json([
          { scenario: "northhill_corp", sweep_id: "20260525", path: "/results/northhill_corp/20260525" },
        ]),
      ),
      http.get("/api/results/:scenario/:sweepId", () =>
        HttpResponse.json({
          sweep_id: "20260525",
          scenario_id: "northhill_corp",
          surface: "mirage",
          models: ["gpt-4.1"],
          seeds: [1],
          tasks: ["triage_tickets"],
          n_runs: 1,
          n_succeeded: 1,
          composite_mean: 0.82,
          composite_by_task: { triage_tickets: 0.82 },
          composite_by_model: { "gpt-4.1": 0.82 },
          cell_by_model_task: {
            "gpt-4.1": {
              triage_tickets: {
                n_runs: 1,
                n_passed_gates: 1,
                composite_mean: 0.82,
                composite_max: 0.82,
                judge_mean: 0.8,
                cost_usd_total: 0.05,
                wallclock_s_p95: 30,
                failure_modes: {},
              },
            },
          },
          failure_modes: {},
          runs: [
            {
              scenario_id: "northhill_corp",
              task_id: "triage_tickets",
              surface: "mirage",
              model: "gpt-4.1",
              seed: 1,
              sweep_id: "20260525",
              passed_gates: true,
              programmatic: { gates: [], fraction_passed: 1, all_passed: true, by_category: {} },
              trajectory: {
                n_turns: 5,
                n_commands: 3,
                n_ops: 10,
                bytes_read: 5000,
                cache_hit_rate: 0.5,
                wallclock_s: 25,
                tokens_in: 1000,
                tokens_out: 500,
                cost_usd: 0.05,
                within_budget: true,
              },
              judge: { scores: { accuracy: 0.9 }, rationale: { accuracy: "Good" }, weighted: 0.8, error: null },
              composite: 0.82,
              failure_modes: [],
              error: null,
            },
          ],
        }),
      ),
    );

    render(<ScoreCardDashboard />);

    const selector = await screen.findByRole("combobox");
    expect(selector).toBeInTheDocument();
    expect(selector).toHaveValue("northhill_corp/20260525");

    expect(await screen.findByText("Scorecard Dashboard")).toBeInTheDocument();
  });
});
