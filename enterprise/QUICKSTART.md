# Quickstart — Run the eval on your laptop

Three steps. Offline (L1) only needs an OpenAI key.

> All commands use `uv run mirage-eval` (hyphen). Always run from inside `enterprise/`.

## 1. Setup

```bash
cd enterprise
uv sync
cp .env.example .env          # then set OPENAI_API_KEY=sk-... in .env
```

## 2. Seed the synthetic corpus (once)

```bash
uv run mirage-eval seed --scenario onboarding_it
```

## 3. Run a task

```bash
uv run mirage-eval run \
  --scenario onboarding_it \
  --task onboarding_status \
  --model gpt-5-mini \
  --seed 1
```

A scorecard table prints at the end (composite, gates, tokens, cost). Full output lands in:

```
enterprise/results/onboarding_it/<sweep_id>/runs/l1__gpt-5-mini__onboarding_status__seed1/
  scorecard.json         # the numbers from the printed table
  final_output.txt       # agent's final reply
  output_files/          # files the agent wrote (e.g. onboarding_status.md)
  artifacts.json         # full run record
  sessions.jsonl         # per-turn trace
```

Other tasks: `provision_new_hire`, `ticket_triage`, `incident_followup`.

## Optional — sweep + dashboard

```bash
uv run mirage-eval sweep --scenario onboarding_it --models gpt-5-mini --seeds 1 --yes
```

Then open:

- `enterprise/results/onboarding_it/<sweep_id>/SUMMARY.md` — per-task / per-model table.
- `enterprise/canvases/onboarding_it/dashboard.canvas.tsx` — interactive Cursor canvas dashboard.
