# enterprise/ — Mirage Evaluation Harness

Scenario-driven evaluation harness for Mirage agents. Lives in its own folder so it can be merged back to OSS or kept private cleanly. Never modifies anything outside `enterprise/`.

## What this is

A graded benchmark for agents that drive a Mirage `Workspace`. For each task we measure:

1. **Programmatic gates** — files written, citations present, banned strings absent, expected resources touched, no `ENOENT`s.
2. **Trajectory metrics** — turns, commands, ops, bytes, cache-hit rate, wallclock, tokens, $cost (parsed from `/.sessions/<date>/<sid>.jsonl`).
3. **LLM-as-judge** — rubric-based quality scoring with a stronger model than the agent.

A composite scorecard blends gates first, then quality. Sweeps run `models × seeds × tasks` matrices and emit a per-scenario Cursor canvas dashboard plus a markdown summary.

## Layout

```
enterprise/
  mirage_eval/                  # scenario-agnostic framework (CLI, runner, scorers, report)
  scenarios/
    onboarding_it/              # ACME Corp new-hire onboarding + IT helpdesk (scenario #1)
    bi_analytics/               # placeholder for the next scenario
  canvases/<scenario>/          # per-scenario interactive dashboards
  results/<scenario>/<sweep>/   # per-sweep run artifacts (gitignored)
  tests/                        # framework-level pytest
  scripts/                      # convenience wrappers
```

## Two evaluation surfaces

- **L1 (synthetic, offline)** — disk-backed fakes that wear the real Slack / GSheets / GDocs prompts. Restored from a snapshot tar so every run is bit-identical. No external services.
- **L2 (real Slack + Google)** — same task YAMLs, mounts swap to real `SlackResource` / `GSheetsResource` / `GDocsResource`. Tickets stay disk-backed via `FakeTicketingResource` (Linear mapping is a future L3 milestone).

## Quickstart

```bash
cd enterprise
uv sync
cp .env.example .env  # fill in OPENAI_API_KEY at minimum

# Phase 1: build the synthetic fixture once
mirage-eval seed --scenario onboarding_it

# Run a single task
mirage-eval run --scenario onboarding_it --task onboarding_status \
                --model gpt-5-mini --seed 1

# Run the full sweep
mirage-eval sweep --scenario onboarding_it \
                  --models gpt-5-mini,gpt-5 --seeds 1,2,3
```

## Adding a new scenario

The framework treats each scenario as a folder with a `scenario.yaml` manifest. To add `bi_analytics` (or anything else):

1. Copy `scenarios/onboarding_it/` to `scenarios/<your-scenario>/`.
2. Rewrite `seed.py` to generate your synthetic corpus on disk.
3. Rewrite `mounts.py::build_l1_workspace` for the mounts you need.
4. Update `scenario.yaml` (id, builder paths, fixture paths).
5. Author tasks in `tasks/`.
6. Run `mirage-eval seed --scenario <your-scenario>` then `mirage-eval run ...`.

The framework code under `mirage_eval/` never touches scenario-specific concerns.
